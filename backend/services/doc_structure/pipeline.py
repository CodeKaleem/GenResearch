from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field

from database.supabase_client import get_supabase
from services.doc_structure.items import PaperItem, extract_items
from services.doc_structure.references import ReferenceEntry, ReferenceBundle, parse_reference_entries_from_pages
from services.doc_structure.sections import Section, extract_sections
from services.doc_structure.text_extract import detect_no_text_layer, extract_pages
from services.doc_structure.paper_type import classify_paper_type

logger = logging.getLogger(__name__)


@dataclass
class DocStructure:
    status: str = "pending"
    page_count: int = 0
    references_start_page: int | None = None
    sections: list[Section] = field(default_factory=list)
    references: list[ReferenceEntry] = field(default_factory=list)
    items: list[PaperItem] = field(default_factory=list)
    paper_type: str = "unknown"
    body_char_coverage: float = 0.0
    section_count: int = 0
    reference_count: int = 0
    expected_reference_count: int = 0
    missing_reference_ids: list[int] = field(default_factory=list)
    error: str | None = None


async def persist_structure(user_id: str, paper_id: str, structure: DocStructure) -> None:
    """Persist a structure summary best-effort without failing the request path."""
    try:
        sb = get_supabase()
    except Exception as exc:
        logger.warning("paper_structure_persist_unavailable", extra={"paper_id": paper_id, "error": str(exc)})
        return

    try:
        payload = {
            "paper_id": paper_id,
            "user_id": user_id,
            "status": structure.status,
            "extractor_version": "1",
            "page_count": structure.page_count,
            "references_start_page": structure.references_start_page,
            "reference_count": structure.reference_count,
            "expected_reference_count": structure.expected_reference_count,
            "missing_reference_ids": structure.missing_reference_ids,
            "section_count": structure.section_count,
            "body_char_coverage": structure.body_char_coverage,
            "paper_type": structure.paper_type,
            "error": structure.error,
        }
        sb.table("paper_structure").upsert(payload, on_conflict="paper_id").execute()

        sb.table("paper_sections").delete().eq("paper_id", paper_id).execute()
        if structure.sections:
            rows = [{
                "paper_id": paper_id,
                "user_id": user_id,
                "ordinal": section.ordinal,
                "level": section.level,
                "title": section.title,
                "page_start": section.page_start,
                "page_end": section.page_end,
                "text": section.text,
                "cited_refs": section.cited_refs,
                "is_fallback_window": section.is_fallback_window,
            } for section in structure.sections]
            if rows:
                sb.table("paper_sections").insert(rows).execute()

        sb.table("paper_references").delete().eq("paper_id", paper_id).execute()
        if structure.references:
            rows = [{
                "paper_id": paper_id,
                "user_id": user_id,
                "ref_number": ref.ref_number,
                "raw": ref.raw,
                "authors": ref.authors,
                "title": ref.title,
                "year": ref.year,
                "venue": ref.venue,
                "doi": ref.doi,
                "arxiv_id": ref.arxiv_id,
                "parse_confidence": ref.parse_confidence,
                "verified": ref.verified,
                "verification_source": ref.verification_source,
            } for ref in structure.references]
            if rows:
                sb.table("paper_references").insert(rows).execute()

        sb.table("paper_items").delete().eq("paper_id", paper_id).execute()
        if structure.items:
            rows = [{
                "paper_id": paper_id,
                "user_id": user_id,
                "kind": item.kind,
                "label": item.label,
                "caption": item.caption,
                "page": item.page,
            } for item in structure.items]
            if rows:
                sb.table("paper_items").insert(rows).execute()
    except Exception as exc:
        logger.warning("paper_structure_persist_failed", extra={"paper_id": paper_id, "error": str(exc)}, exc_info=True)


def extract_structure(pdf_bytes: bytes) -> DocStructure:
    page_texts = extract_pages(pdf_bytes)
    page_count = len(page_texts)
    if not page_texts or detect_no_text_layer(pdf_bytes):
        return DocStructure(status="no_text_layer", page_count=page_count, paper_type="unknown", error="No text layer detected.")

    ref_bundle = parse_reference_entries_from_pages(page_texts)
    ref_text = "\n\n".join(page_texts[ref_bundle.references_start_page - 1:]) if ref_bundle.references_start_page else ""
    sections = extract_sections(pdf_bytes, ref_bundle.references_start_page)
    body_text = "\n\n".join(page_texts[: max(0, (ref_bundle.references_start_page or 1) - 1)]) if ref_bundle.references_start_page else "\n\n".join(page_texts)
    referenced_chars = sum(len(section.text) for section in sections if section.text)
    body_chars = max(1, len(body_text))
    body_char_coverage = min(1.0, referenced_chars / body_chars) if body_chars else 0.0
    item_text = "\n\n".join(page_texts)
    items = extract_items(item_text)
    title = ""
    abstract = ""
    if page_texts:
        chunks = page_texts[:2]
        title = chunks[0][:200] if chunks else ""
        abstract = " ".join(chunks[1:3])[:600] if len(chunks) > 1 else ""
    paper_type = classify_paper_type(title, abstract)
    structure = DocStructure(
        status="ready" if ref_bundle.entries else "partial",
        page_count=page_count,
        references_start_page=ref_bundle.references_start_page,
        sections=sections,
        references=ref_bundle.entries,
        items=items,
        paper_type=paper_type,
        body_char_coverage=body_char_coverage,
        section_count=len(sections),
        reference_count=ref_bundle.reference_count,
        expected_reference_count=ref_bundle.expected_reference_count,
        missing_reference_ids=ref_bundle.missing_reference_ids,
    )
    if ref_bundle.reference_count == 0 and not sections:
        structure.status = "partial"
    return structure
