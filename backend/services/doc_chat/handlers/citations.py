from __future__ import annotations

import asyncio
import os

from database.supabase_client import get_supabase
from services.doc_structure.pipeline import extract_structure, persist_structure


async def handle_citations(user_id: str, query: str, *, paper_id: str | None = None, top_k: int = 5):
    sb = get_supabase()
    papers = []
    if paper_id:
        res = sb.table("papers").select("id, user_id, title, storage_path").eq("id", paper_id).eq("user_id", user_id).execute()
        papers = res.data or []
    else:
        res = sb.table("papers").select("id, user_id, title, storage_path").eq("user_id", user_id).execute()
        papers = res.data or []

    if not papers:
        return {
            "answer": "No papers are available for citation extraction.",
            "sources": [],
            "chunks_used": 0,
            "model": "doc-structure",
            "intent": "citations",
            "coverage": {"unit": "references", "covered": 0, "total": 0, "percent": 0.0, "missing": []},
            "items": None,
        }

    blocks = []
    for paper in papers:
        storage_path = paper.get("storage_path")
        if not storage_path or not os.path.exists(storage_path):
            blocks.append({"paper_id": paper["id"], "title": paper.get("title", "Untitled"), "answer": "Structure not available yet; please rebuild the document structure first."})
            continue
        try:
            with open(storage_path, "rb") as fh:
                pdf_bytes = fh.read()
            structure = await asyncio.to_thread(extract_structure, pdf_bytes)
            await persist_structure(user_id, paper["id"], structure)
            lines = [f"[{ref.ref_number}] {ref.raw}" for ref in structure.references]
            coverage = {
                "unit": "references",
                "covered": structure.reference_count,
                "total": structure.expected_reference_count,
                "percent": round((structure.reference_count / structure.expected_reference_count) * 100, 1) if structure.expected_reference_count else 0.0,
                "missing": [int(v) for v in structure.missing_reference_ids],
            }
            header = f"Extracted {structure.reference_count} of {structure.expected_reference_count} reference entries ({coverage['percent']}%)."
            if structure.missing_reference_ids:
                header += f" Missing: {', '.join(f'[{v}]' for v in structure.missing_reference_ids)}"
            answer = header + "\n\n" + "\n".join(lines) if lines else header + "\n\nNo reference entries were parsed."
            blocks.append({"paper_id": paper["id"], "title": paper.get("title", "Untitled"), "answer": answer, "coverage": coverage})
        except Exception:
            blocks.append({"paper_id": paper["id"], "title": paper.get("title", "Untitled"), "answer": "Structure is not available yet for this paper.", "coverage": {"unit": "references", "covered": 0, "total": 0, "percent": 0.0, "missing": []}})

    answer = "\n\n---\n\n".join(item["answer"] for item in blocks)
    return {
        "answer": answer,
        "sources": [{"paper_id": item["paper_id"], "title": item["title"], "relevance": 1.0} for item in blocks],
        "chunks_used": 0,
        "model": "doc-structure",
        "intent": "citations",
        "coverage": blocks[0].get("coverage") if blocks else {"unit": "references", "covered": 0, "total": 0, "percent": 0.0, "missing": []},
        "items": None,
    }
