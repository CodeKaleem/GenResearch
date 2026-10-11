from __future__ import annotations

import asyncio
import logging
import os
import re

# ============================================================
# GenResearch — Citation Agent
# Extracts and formats citations from research papers
# ============================================================
from database.supabase_client import get_supabase
from services.doc_structure.pipeline import extract_structure, persist_structure
from services.doc_structure.references import ReferenceEntry
from services.llm_service import call_llm
from services.rag_service import semantic_search

logger = logging.getLogger(__name__)

CITATION_SYSTEM = """You are GenResearch Citation Agent, an expert in academic citation management.
Your task is to extract and format references from the provided paper excerpts.

CRITICAL RULES:
1. ONLY extract references that actually exist in the provided text.
2. DO NOT fabricate, guess, or invent citations.
3. DO NOT repeat or duplicate any citation under multiple numbers.
4. If a reference has incomplete details, include only what is stated.
5. Format citations in the requested style cleanly and number them sequentially.
6. At the end, state the total citation count."""

CITATION_STYLES = {
    "apa": "APA 7th Edition (Author, Year. Title. Journal, Volume(Issue), Pages. DOI)",
    "mla": "MLA 9th Edition (Author. \"Title.\" Journal, vol. X, no. X, Year, pp. X-X.)",
    "ieee": "IEEE ([1] Author, \"Title,\" Journal, vol. X, no. X, pp. X-X, Year.)",
    "chicago": "Chicago 17th (Author. \"Title.\" Journal Volume, no. Issue (Year): Pages.)",
}


def _clean_ref_string(raw: str) -> str:
    cleaned = raw.replace("\u00ad", "").replace("\u200b", "").replace("\ufeff", "")
    # Unwrap URLs and DOIs that were broken across newlines
    cleaned = re.sub(r"(https?://\S*?)\n([^\s\n]+)", r"\1\2", cleaned)
    cleaned = re.sub(r"(10\.\d{4,9}/\S*?)\n([^\s\n]+)", r"\1\2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _format_reference_entry(ref: ReferenceEntry, idx: int, style: str) -> str:
    cleaned_raw = _clean_ref_string(ref.raw)
    # Strip any existing leading numbering like "1. ", "[1] ", "\t 1.\t "
    cleaned_body = re.sub(r"^(?:\[\d+\]|\d+\.|\(\d+\))\s*", "", cleaned_raw).strip()

    doi_suffix = ""
    if ref.doi and ref.doi not in cleaned_body and f"doi.org/{ref.doi}" not in cleaned_body:
        doi_suffix = f" https://doi.org/{ref.doi}"

    s = style.lower()
    if s == "ieee":
        return f"[{idx}] {cleaned_body}{doi_suffix}".strip()
    else:
        return f"{idx}. {cleaned_body}{doi_suffix}".strip()


async def run_citation_extraction(
    user_id: str,
    paper_ids: list[str],
    style: str = "apa",
) -> dict:
    """
    Extract and format genuine citations from papers with document-structure awareness.
    """
    style_desc = CITATION_STYLES.get(style.lower(), CITATION_STYLES["apa"])
    sb = get_supabase()

    async def extract_paper(paper_id: str) -> dict:
        # Step 1: Look up paper metadata from DB
        title = "Untitled Paper"
        storage_path = None
        try:
            p_data = (
                sb.table("papers")
                .select("id, title, storage_path")
                .eq("id", paper_id)
                .execute()
                .data
            )
            if p_data:
                title = p_data[0].get("title") or title
                storage_path = p_data[0].get("storage_path")
        except Exception as exc:
            logger.warning("citation_paper_lookup_failed: %s", exc)

        references: list[ReferenceEntry] = []

        # Step 2: Try extracting directly from PDF document structure
        if storage_path and os.path.exists(storage_path):
            try:
                def _read_pdf_and_extract():
                    with open(storage_path, "rb") as f:
                        pdf_bytes = f.read()
                    return extract_structure(pdf_bytes)

                structure = await asyncio.to_thread(_read_pdf_and_extract)
                if structure and structure.references:
                    references = structure.references
                    # Best-effort caching in Supabase
                    asyncio.create_task(persist_structure(user_id, paper_id, structure))
            except Exception as exc:
                logger.warning("pdf_reference_extraction_failed: %s", exc)

        # Step 3: If PDF extraction yielded real references, format them deterministically
        if references:
            formatted_list = []
            for idx, ref in enumerate(references, start=1):
                formatted_list.append(_format_reference_entry(ref, idx, style))

            header = f"Extracted {len(references)} references from \"{title}\" ({style.upper()} format):\n\n"
            citations_text = header + "\n\n".join(formatted_list) + f"\n\nTotal citations: {len(references)}"

            return {
                "paper_id": paper_id,
                "title": title,
                "citations_text": citations_text,
                "style": style.upper(),
                "count": len(references),
                "chunks_used": 0,
                "status": "completed",
            }

        # Step 4: Fallback to chunk retrieval + LLM extraction if PDF extraction was unavailable
        chunks = await semantic_search(
            user_id=user_id,
            query="references bibliography citations authors doi journal publication year",
            top_k=15,
            paper_id=paper_id,
        )

        if not chunks:
            return {
                "paper_id": paper_id,
                "title": title,
                "citations_text": "No content found for this paper.",
                "count": 0,
                "status": "empty",
            }

        if title == "Untitled Paper":
            title = chunks[0].get("title", "Untitled Paper")

        context = "\n\n---\n\n".join(
            f"[Excerpt {i+1}]\n{c['text']}" for i, c in enumerate(chunks)
        )

        prompt = f"""Extract all academic citations and references from the following excerpts of the paper "{title}".

Citation Style Required: {style_desc}

--- PAPER EXCERPTS ---

{context}

--- END OF EXCERPTS ---

Extract, deduplicate, and format all citations found without repeating any reference:"""

        citations_text = await call_llm(
            prompt=prompt,
            agent_role="citation_extraction",
            system=CITATION_SYSTEM,
            temperature=0.05,
            max_tokens=3000,
        )

        return {
            "paper_id": paper_id,
            "title": title,
            "citations_text": citations_text,
            "style": style.upper(),
            "count": len(re.findall(r"(?m)^\s*(?:\[\d+\]|\d+\.)", citations_text)),
            "chunks_used": len(chunks),
            "status": "completed",
        }

    all_citations = await asyncio.gather(
        *(extract_paper(paper_id) for paper_id in paper_ids)
    )

    return {
        "agent": "citation",
        "results": all_citations,
        "style": style.upper(),
        "total_papers": len(paper_ids),
    }
