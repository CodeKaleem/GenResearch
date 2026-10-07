from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from database.supabase_client import get_supabase
from services.doc_structure.pipeline import extract_structure, persist_structure

router = APIRouter(prefix="/papers", tags=["paper-structure"])
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "pdfs"


async def _read_pdf_for_user(user_id: str, paper_id: str) -> bytes:
    sb = get_supabase()
    res = sb.table("papers").select("storage_path, user_id").eq("id", paper_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Paper not found.")
    storage_path = res.data[0].get("storage_path") or str(STORAGE_DIR / user_id / f"{paper_id}.pdf")
    if not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="Stored PDF not found.")
    with open(storage_path, "rb") as handle:
        return handle.read()


@router.post("/{paper_id}/structure/rebuild")
async def rebuild_structure(paper_id: str, user_id: str):
    pdf_bytes = await _read_pdf_for_user(user_id, paper_id)
    structure = await asyncio.to_thread(extract_structure, pdf_bytes)
    await persist_structure(user_id, paper_id, structure)
    return {
        "paper_id": paper_id,
        "status": structure.status,
        "reference_count": structure.reference_count,
        "expected_reference_count": structure.expected_reference_count,
        "missing_reference_ids": structure.missing_reference_ids,
    }


@router.get("/{paper_id}/structure")
async def get_structure(paper_id: str, user_id: str):
    sb = get_supabase()
    result = sb.table("paper_structure").select("*").eq("paper_id", paper_id).eq("user_id", user_id).execute()
    if not result.data:
        return {"paper_id": paper_id, "status": "not_found", "reference_count": 0, "expected_reference_count": 0, "missing_reference_ids": []}
    row = result.data[0]
    return {
        "paper_id": paper_id,
        "status": row.get("status"),
        "reference_count": row.get("reference_count", 0),
        "expected_reference_count": row.get("expected_reference_count", 0),
        "missing_reference_ids": row.get("missing_reference_ids", []),
        "section_count": row.get("section_count", 0),
        "body_char_coverage": row.get("body_char_coverage", 0.0),
        "paper_type": row.get("paper_type"),
    }


@router.get("/{paper_id}/references")
async def get_references(paper_id: str, user_id: str, format: str = Query("json")):
    sb = get_supabase()
    result = sb.table("paper_references").select("*").eq("paper_id", paper_id).eq("user_id", user_id).order("ref_number", desc=False).execute()
    rows = result.data or []
    if format == "json":
        return {"paper_id": paper_id, "references": rows}
    if format == "csv":
        header = "ref_number,authors,title,year,venue,doi,arxiv_id,raw"
        lines = [header]
        for row in rows:
            lines.append(
                ",".join([
                    str(row.get("ref_number", "")),
                    str(row.get("authors", "") or "").replace(",", " "),
                    str(row.get("title", "") or "").replace(",", " "),
                    str(row.get("year", "") or ""),
                    str(row.get("venue", "") or "").replace(",", " "),
                    str(row.get("doi", "") or ""),
                    str(row.get("arxiv_id", "") or ""),
                    str(row.get("raw", "") or "").replace("\n", " "),
                ])
            )
        return {"paper_id": paper_id, "format": "csv", "content": "\n".join(lines)}
    if format == "bibtex":
        lines = []
        for row in rows:
            title = row.get("title") or "Untitled"
            authors = row.get("authors") or row.get("raw") or "Unknown"
            year = row.get("year") or "n.d."
            doi = row.get("doi") or ""
            lines.append(f"@article{{ref{row.get('ref_number', 'na')} , author = {{ {authors} }}, title = {{ {title} }}, year = {{ {year} }}, doi = {{ {doi} }} }}")
        return {"paper_id": paper_id, "format": "bibtex", "content": "\n".join(lines)}
    if format == "ris":
        lines = []
        for row in rows:
            lines.append(f"TY  - JOUR\nTI  - {row.get('title') or row.get('raw') or 'Untitled'}\nAU  - {row.get('authors') or 'Unknown'}\nPY  - {row.get('year') or ''}\nDO  - {row.get('doi') or ''}\nER\n")
        return {"paper_id": paper_id, "format": "ris", "content": "\n".join(lines)}
    raise HTTPException(status_code=400, detail="Unsupported reference export format.")
