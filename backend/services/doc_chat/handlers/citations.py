from __future__ import annotations

import asyncio
import logging
import os

from database.supabase_client import get_supabase
from services.doc_structure.pipeline import extract_structure, persist_structure

logger = logging.getLogger(__name__)

_EMPTY_COVERAGE = {"unit": "references", "covered": 0, "total": 0, "percent": 0.0, "missing": []}


def _percent(covered: int, total: int) -> float:
    return round((covered / total) * 100, 1) if total else 0.0


def _load_stored(sb, user_id: str, paper_id: str) -> dict | None:
    """Read the structure persisted at upload time. Blocking: run in a thread."""
    structure = (
        sb.table("paper_structure")
        .select("status, reference_count, expected_reference_count, missing_reference_ids")
        .eq("paper_id", paper_id)
        .eq("user_id", user_id)
        .execute()
    ).data or []
    if not structure or structure[0].get("status") not in {"ready", "partial"}:
        return None
    refs = (
        sb.table("paper_references")
        .select("ref_number, raw")
        .eq("paper_id", paper_id)
        .eq("user_id", user_id)
        .order("ref_number", desc=False)
        .execute()
    ).data or []
    if not refs:
        return None
    row = structure[0]
    return {
        "lines": [f"[{r['ref_number']}] {r['raw']}" for r in refs],
        "covered": row.get("reference_count") or len(refs),
        "total": row.get("expected_reference_count") or 0,
        "missing": [int(v) for v in (row.get("missing_reference_ids") or [])],
    }


def _extract_from_pdf(storage_path: str) -> dict | None:
    """Slow path: parse the PDF. Blocking: run in a thread."""
    with open(storage_path, "rb") as fh:
        pdf_bytes = fh.read()
    structure = extract_structure(pdf_bytes)
    return {
        "structure": structure,
        "lines": [f"[{ref.ref_number}] {ref.raw}" for ref in structure.references],
        "covered": structure.reference_count,
        "total": structure.expected_reference_count,
        "missing": [int(v) for v in structure.missing_reference_ids],
    }


async def _references_for_paper(sb, user_id: str, paper: dict) -> dict:
    title = paper.get("title", "Untitled")

    # Fast path: references were already extracted and persisted at upload time.
    try:
        stored = await asyncio.to_thread(_load_stored, sb, user_id, paper["id"])
    except Exception as exc:
        logger.info("stored_references_unavailable: %s", exc)
        stored = None

    if stored is None:
        storage_path = paper.get("storage_path")
        if not storage_path or not os.path.exists(storage_path):
            return {"paper_id": paper["id"], "title": title, "answer": "Structure not available yet; please rebuild the document structure first.", "coverage": dict(_EMPTY_COVERAGE)}
        try:
            extracted = await asyncio.to_thread(_extract_from_pdf, storage_path)
            await persist_structure(user_id, paper["id"], extracted["structure"])  # so next time is instant
            stored = extracted
        except Exception:
            logger.warning("reference_extraction_failed", extra={"paper_id": paper["id"]}, exc_info=True)
            return {"paper_id": paper["id"], "title": title, "answer": "Structure is not available yet for this paper.", "coverage": dict(_EMPTY_COVERAGE)}

    coverage = {
        "unit": "references",
        "covered": stored["covered"],
        "total": stored["total"],
        "percent": _percent(stored["covered"], stored["total"]),
        "missing": stored["missing"],
    }
    header = f"Extracted {stored['covered']} of {stored['total']} reference entries ({coverage['percent']}%)."
    if stored["missing"]:
        header += f" Missing: {', '.join(f'[{v}]' for v in stored['missing'])}"
    answer = header + "\n\n" + "\n".join(stored["lines"]) if stored["lines"] else header + "\n\nNo reference entries were parsed."
    return {"paper_id": paper["id"], "title": title, "answer": answer, "coverage": coverage}


async def handle_citations(user_id: str, query: str, *, paper_id: str | None = None, top_k: int = 5):
    sb = get_supabase()

    def _load_papers():
        q = sb.table("papers").select("id, user_id, title, storage_path").eq("user_id", user_id)
        if paper_id:
            q = q.eq("id", paper_id)
        return q.execute().data or []

    papers = await asyncio.to_thread(_load_papers)

    if not papers:
        return {
            "answer": "No papers are available for citation extraction.",
            "sources": [],
            "chunks_used": 0,
            "model": "doc-structure",
            "intent": "citations",
            "coverage": dict(_EMPTY_COVERAGE),
            "items": None,
        }

    blocks = list(await asyncio.gather(*(_references_for_paper(sb, user_id, paper) for paper in papers)))

    if len(blocks) > 1:  # several papers: label each block
        answer = "\n\n---\n\n".join(f"## {b['title']}\n\n{b['answer']}" for b in blocks)
    else:
        answer = blocks[0]["answer"]

    covered = sum(b["coverage"]["covered"] for b in blocks)
    total = sum(b["coverage"]["total"] for b in blocks)
    coverage = {
        "unit": "references",
        "covered": covered,
        "total": total,
        "percent": _percent(covered, total),
        "missing": blocks[0]["coverage"]["missing"] if len(blocks) == 1 else [],
    }
    return {
        "answer": answer,
        "sources": [{"paper_id": b["paper_id"], "title": b["title"], "relevance": 1.0} for b in blocks],
        "chunks_used": 0,
        "model": "doc-structure",
        "intent": "citations",
        "coverage": coverage,
        "items": None,
    }
