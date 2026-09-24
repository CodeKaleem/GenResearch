"""Section-aware retrieval primitives for proposal composition."""
from __future__ import annotations

from collections import defaultdict

from models.schemas import RetrievedChunk
from services.rag_service import semantic_search


SECTION_QUERIES = {
    "overview": "abstract introduction objectives scope research questions",
    "methodology": "method methodology study design data collection sample participants",
    "results": "results findings statistics table figure quantitative qualitative",
    "discussion": "discussion implications interpretation comparison trends",
    "challenges_limits": "challenges limitations threats to validity future work",
    "conclusion": "conclusion contributions summary recommendations",
}


def reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Merge ranked result lists without assuming score scales are comparable."""
    scores: defaultdict[str, float] = defaultdict(float)
    records: dict[str, dict] = {}
    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            chunk_id = result.get("id") or result.get("chunk_id")
            if not chunk_id:
                continue
            scores[chunk_id] += 1 / (k + rank)
            records[chunk_id] = result
    return [records[chunk_id] | {"fusion_score": scores[chunk_id]} for chunk_id in sorted(scores, key=scores.get, reverse=True)]


def _as_retrieved_chunk(hit: dict, score: float) -> RetrievedChunk:
    metadata = hit.get("metadata") or {}
    return RetrievedChunk(
        chunk_id=hit.get("id", ""),
        paper_id=hit.get("paper_id") or metadata.get("paper_id", ""),
        title=hit.get("title") or metadata.get("title"),
        authors=metadata.get("authors", []),
        year=metadata.get("year"),
        section_heading=metadata.get("section_heading"),
        page=metadata.get("page"),
        chunk_index=hit.get("chunk_index", metadata.get("chunk_index", 0)),
        char_start=metadata.get("char_start"),
        char_end=metadata.get("char_end"),
        is_table=bool(metadata.get("is_table", False)),
        table_data=metadata.get("table_data"),
        text=hit.get("text", ""),
        score=score,
    )


async def retrieve_by_sections(
    user_id: str,
    paper_id: str,
    top_k_per_query: int = 5,
) -> dict[str, list[RetrievedChunk]]:
    """Retrieve and fuse evidence separately for each proposal section."""
    sections: dict[str, list[RetrievedChunk]] = {}
    for section, query in SECTION_QUERIES.items():
        dense_hits = await semantic_search(user_id, query, top_k_per_query * 2, paper_id)
        fused = reciprocal_rank_fusion([dense_hits])[:top_k_per_query]
        sections[section] = [
            _as_retrieved_chunk(hit, float(hit.get("fusion_score", 0)))
            for hit in fused
        ]
    return sections