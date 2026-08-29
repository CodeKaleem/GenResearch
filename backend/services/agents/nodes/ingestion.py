# ============================================================
# Node: Ingestion + Citation Registry (Stage 8)
# Builds the citation registry and embeds sources into ChromaDB.
# No LLM call — pure data processing.
# ============================================================
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from services.chroma_service import store_chunks
from services.chunker import chunk_text

logger = logging.getLogger(__name__)


def _build_citation_id(index: int) -> str:
    return f"CR-{index + 1:03d}"


async def ingestion_node(state: dict) -> dict:
    user_id = state.get("user_id", "anonymous")
    session_id = state.get("session_id", str(uuid.uuid4()))
    quality_results = state.get("source_quality_results", {})

    user_sources = state.get("user_provided_sources", [])
    scraped_sources = state.get("scraped_sources", [])

    # Filter scraped by quality eval
    accepted_scraped = [
        s for s in scraped_sources
        if quality_results.get(s.get("title", ""), {}).get("passed", True)
    ]

    # Build citation registry — user sources first (priority)
    citation_registry: list[dict] = []
    all_accepted = []

    for s in user_sources:
        cid = _build_citation_id(len(citation_registry))
        citation_registry.append({
            "id": cid, "title": s.get("title", "User Document"),
            "authors": s.get("authors", "Unknown"), "year": s.get("year"),
            "url": s.get("url", ""), "doi": s.get("doi", ""),
            "accessed_date": datetime.utcnow().isoformat(),
            "tag": "user", "source_type": s.get("source_type", "uploaded"),
            "abstract_snippet": s.get("abstract_snippet", ""),
        })
        all_accepted.append({**s, "tag": "user", "citation_id": cid})

    for s in accepted_scraped:
        cid = _build_citation_id(len(citation_registry))
        citation_registry.append({
            "id": cid, "title": s.get("title", "Unknown"),
            "authors": s.get("authors", "Unknown"), "year": s.get("year"),
            "url": s.get("url", ""), "doi": s.get("doi", ""),
            "accessed_date": s.get("accessed_date", datetime.utcnow().isoformat()),
            "tag": "scraped", "source_type": s.get("source_api", "web"),
            "abstract_snippet": s.get("abstract_snippet", ""),
        })
        all_accepted.append({**s, "tag": "scraped", "citation_id": cid})

    # Ingest into ChromaDB
    total_chunks = 0
    for source in all_accepted:
        content = source.get("abstract_snippet", "") or source.get("content", "")
        if not content:
            continue
        chunks = chunk_text(content)
        if chunks:
            num = await store_chunks(
                user_id=user_id, paper_id=source.get("citation_id", str(uuid.uuid4())),
                chunks=chunks, title=source.get("title", "Unknown"),
                collection_name=f"session_{session_id}",
            )
            total_chunks += num

    return {
        "citation_registry": citation_registry,
        "current_step": "ingestion",
        "steps_log": [
            f"✓ Registry: {len(citation_registry)} sources, {total_chunks} chunks embedded"
        ],
    }
