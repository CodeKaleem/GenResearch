# ============================================================
# GenResearch — Papers Router
# Upload PDFs → Extract → Chunk → Embed → Store in ChromaDB
# Sync metadata to Supabase papers table
# ============================================================
import uuid
import logging
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from database.supabase_client import get_supabase
from services.pdf_extractor import extract_text_from_pdf, get_pdf_page_count
from services.chunker import chunk_text
from services.chroma_service import store_chunks, delete_paper_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "pdfs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MAX_PAPERS_PER_USER = 20

def _format_file_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _check_user_quota(sb, user_id: str):
    """Enforce user quota: max 20 papers."""
    res = sb.table("papers").select("id").eq("user_id", user_id).execute()
    papers = res.data or []
    if len(papers) >= MAX_PAPERS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"User quota exceeded: Maximum {MAX_PAPERS_PER_USER} papers allowed per account.",
        )


def _save_pdf_file(user_id: str, paper_id: str, file_bytes: bytes) -> str:
    """Save raw PDF file to server storage."""
    user_dir = STORAGE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / f"{paper_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return str(file_path)



# ── POST /papers/upload ──────────────────────────────────────
@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    title: str = Form(""),
    authors: str = Form(""),
    year: int = Form(None),
    collection: str = Form(""),
    tags: str = Form(""),  # comma-separated
):
    """
    Upload a single PDF paper:
    1. Insert metadata into Supabase with status='processing'
    2. Extract text from PDF
    3. Chunk text
    4. Embed chunks and store in ChromaDB
    5. Update Supabase with status='indexed' and chunk count
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    file_size = _format_file_size(len(file_bytes))
    paper_id = str(uuid.uuid4())
    paper_title = title or file.filename.rsplit(".", 1)[0]
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    sb = get_supabase()
    _check_user_quota(sb, user_id)

    storage_path = _save_pdf_file(user_id, paper_id, file_bytes)

    # Step 1: Insert into Supabase with status='processing'
    try:
        sb.table("papers").insert({
            "id": paper_id,
            "user_id": user_id,
            "title": paper_title,
            "authors": authors,
            "year": year,
            "file_name": file.filename,
            "file_size": file_size,
            "tags": tag_list,
            "collection": collection,
            "status": "processing",
            "chunks": 0,
            "storage_path": storage_path,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase insert failed: {e}")

    # Step 2–4: Extract → Chunk → Embed → Store
    try:
        text = await extract_text_from_pdf(file_bytes)
        if not text.strip():
            raise ValueError("No text could be extracted from the PDF.")

        pages = await get_pdf_page_count(file_bytes)
        chunks = chunk_text(text)
        num_chunks = await store_chunks(
            user_id=user_id,
            paper_id=paper_id,
            chunks=chunks,
            title=paper_title,
            collection_name=collection,
        )

        # Step 5: Update Supabase with indexed status
        sb.table("papers").update({
            "status": "indexed",
            "chunks": num_chunks,
            "pages": pages,
        }).eq("id", paper_id).execute()

        return {
            "paper_id": paper_id,
            "title": paper_title,
            "file_name": file.filename,
            "file_size": file_size,
            "pages": pages,
            "chunks": num_chunks,
            "status": "indexed",
        }

    except Exception as e:
        # On failure: mark paper as failed
        sb.table("papers").update({"status": "failed"}).eq("id", paper_id).execute()
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {e}",
        )


# ── POST /papers/upload-batch ────────────────────────────────
@router.post("/upload-batch")
async def upload_batch(
    files: list[UploadFile] = File(...),
    user_id: str = Form(...),
    authors: str = Form(""),
    year: int = Form(None),
    collection: str = Form(""),
    tags: str = Form(""),
):
    """Upload multiple PDFs at once. Each file is processed independently."""
    sb = get_supabase()
    _check_user_quota(sb, user_id)

    results = []
    for file in files:
        try:
            # Re-use the single upload logic inline
            file_bytes = await file.read()
            if not file.filename or not file.filename.lower().endswith(".pdf"):
                results.append({
                    "file_name": file.filename,
                    "status": "failed",
                    "error": "Not a PDF file",
                })
                continue

            file_size = _format_file_size(len(file_bytes))
            paper_id = str(uuid.uuid4())
            paper_title = (file.filename or "Untitled").rsplit(".", 1)[0]
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

            storage_path = _save_pdf_file(user_id, paper_id, file_bytes)

            sb.table("papers").insert({
                "id": paper_id,
                "user_id": user_id,
                "title": paper_title,
                "authors": authors,
                "year": year,
                "file_name": file.filename,
                "file_size": file_size,
                "tags": tag_list,
                "collection": collection,
                "status": "processing",
                "chunks": 0,
                "storage_path": storage_path,
            }).execute()

            text = await extract_text_from_pdf(file_bytes)
            if not text.strip():
                sb.table("papers").update({"status": "failed"}).eq("id", paper_id).execute()
                results.append({
                    "paper_id": paper_id,
                    "file_name": file.filename,
                    "status": "failed",
                    "error": "No text extracted",
                })
                continue

            pages = await get_pdf_page_count(file_bytes)
            chunks = chunk_text(text)
            num_chunks = await store_chunks(
                user_id=user_id,
                paper_id=paper_id,
                chunks=chunks,
                title=paper_title,
                collection_name=collection,
            )

            sb.table("papers").update({
                "status": "indexed",
                "chunks": num_chunks,
                "pages": pages,
            }).eq("id", paper_id).execute()

            results.append({
                "paper_id": paper_id,
                "file_name": file.filename,
                "file_size": file_size,
                "pages": pages,
                "chunks": num_chunks,
                "status": "indexed",
            })

        except Exception as e:
            logger.error(f"Error processing batch upload for {file.filename}: {e}", exc_info=True)
            if 'paper_id' in locals() and 'sb' in locals():
                try:
                    sb.table("papers").update({"status": "failed"}).eq("id", paper_id).execute()
                except Exception as update_error:
                    logger.error(f"Failed to update status to 'failed' for {paper_id}: {update_error}")
            
            results.append({
                "file_name": file.filename,
                "status": "failed",
                "error": str(e),
            })

    return {"uploaded": len(results), "results": results}


# ── DELETE /papers/{paper_id} ────────────────────────────────
@router.delete("/{paper_id}")
async def delete_paper(paper_id: str, user_id: str):
    """
    Delete a paper from both ChromaDB and Supabase.
    """
    sb = get_supabase()

    # Verify paper exists and belongs to user
    result = sb.table("papers").select("id, user_id, storage_path").eq("id", paper_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found.")

    paper = result.data[0]
    if paper["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this paper.")

    # Remove stored PDF file if it exists
    storage_path = paper.get("storage_path") or str(STORAGE_DIR / user_id / f"{paper_id}.pdf")
    if os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except Exception as err:
            logger.warning(f"Could not remove PDF file {storage_path}: {err}")

    # Delete chunks from ChromaDB
    deleted_chunks = delete_paper_chunks(user_id, paper_id)

    # Delete row from Supabase
    sb.table("papers").delete().eq("id", paper_id).execute()

    return {"deleted": True, "paper_id": paper_id, "chunks_removed": deleted_chunks}


# ── GET /papers/{paper_id}/download ──────────────────────────
@router.get("/{paper_id}/download")
async def download_paper(paper_id: str, user_id: str):
    """Serve the stored PDF file for download."""
    sb = get_supabase()
    res = sb.table("papers").select("id, user_id, file_name, storage_path").eq("id", paper_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Paper not found.")

    paper = res.data[0]
    file_path = paper.get("storage_path") or str(STORAGE_DIR / user_id / f"{paper_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on server storage.")

    return FileResponse(path=file_path, filename=paper.get("file_name", "paper.pdf"), media_type="application/pdf")


# ── GET /papers/ ─────────────────────────────────────────────
@router.get("/")
async def list_papers(user_id: str):
    """Return all papers for a given user from Supabase."""
    sb = get_supabase()
    result = (
        sb.table("papers")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"papers": result.data}
