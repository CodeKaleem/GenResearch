# ============================================================
# GenResearch — Papers Router
# Upload PDFs → Extract → Chunk → Embed → Store in ChromaDB
# Sync metadata to Supabase papers table
# ============================================================
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database.supabase_client import get_supabase
from services.pdf_extractor import extract_text_from_pdf, get_pdf_page_count
from services.chunker import chunk_text
from services.chroma_service import store_chunks, delete_paper_chunks

router = APIRouter(prefix="/papers", tags=["papers"])


def _format_file_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


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

            sb = get_supabase()

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
    result = sb.table("papers").select("id, user_id").eq("id", paper_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found.")

    paper = result.data[0]
    if paper["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this paper.")

    # Delete chunks from ChromaDB
    deleted_chunks = delete_paper_chunks(user_id, paper_id)

    # Delete row from Supabase
    sb.table("papers").delete().eq("id", paper_id).execute()

    return {"deleted": True, "paper_id": paper_id, "chunks_removed": deleted_chunks}


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
