from __future__ import annotations

import logging
import re

from services.rag_service import semantic_search_session

logger = logging.getLogger(__name__)

_SYNTHESIS_SECTIONS = {"abstract", "introduction", "discussion", "conclusion", "summary"}

_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "and", "or", "to", "with", "is", "are",
    "this", "that", "by", "from", "as", "at", "be", "can", "will", "their", "its", "into",
    "about", "using", "based", "study", "paper", "research", "review",
}


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]{3,}", text.lower()) if w not in _STOPWORDS}


def _select_relevant_sources(section_name: str, guidance: str, registry: list[dict], limit: int = 3) -> list[dict]:
    """
    Pick the registry entries most relevant to THIS section, instead of
    handing every section the same top-N slice of the registry regardless
    of topic. The previous `registry[:3]` approach meant a Methodology
    section could be "assigned" sources that were actually about diagnostic
    imaging, with no way for the draft agent to tell they didn't fit.

    Uses simple keyword overlap rather than a new embedding call — cheap,
    deterministic, and good enough to stop handing clearly-irrelevant
    sources to a section. If nothing overlaps, returns an honest empty list
    rather than falling back to an arbitrary slice — the draft prompt
    already handles "no sources for this section" correctly.
    """
    registry = [source for source in registry if source.get("evidence_level") != "none"]
    if not registry:
        return []

    section_tokens = _tokenize(f"{section_name} {guidance}")
    if not section_tokens:
        return list(registry[:limit])

    scored = []
    for source in registry:
        source_text = f"{source.get('title', '')} {source.get('abstract_snippet', '')}"
        overlap = len(section_tokens & _tokenize(source_text))
        if overlap > 0:
            scored.append((overlap, source))

    if not scored:
        return []

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [source for _, source in scored[:limit]]


def _sources_from_hits(
    hits: list[dict], registry: list[dict], limit: int = 4
) -> list[dict]:
    """Rank distinct registry sources by their best section-retrieval distance."""
    eligible = {
        source.get("id"): source
        for source in registry
        if source.get("id") and source.get("evidence_level") != "none"
    }
    best_hits: dict[str, tuple[float, int]] = {}
    for hit in hits:
        source_id = hit.get("source_id")
        source = eligible.get(source_id)
        if source is None:
            continue
        overlap = len(
            _tokenize(f"{source.get('title', '')} {source.get('abstract_snippet', '')}")
            & _tokenize(hit.get("text", ""))
        )
        distance = float(hit.get("distance", 1.0))
        previous = best_hits.get(source_id)
        if previous is None or (distance, -overlap) < (previous[0], -previous[1]):
            best_hits[source_id] = (distance, overlap)

    ranked_ids = sorted(
        best_hits,
        key=lambda source_id: (
            best_hits[source_id][0],
            -best_hits[source_id][1],
        ),
    )
    return [eligible[source_id] for source_id in ranked_ids[:limit]]


async def context_build_node(state: dict) -> dict:
    """
    Build section-level working context before drafting.

    Each section gets:
    - its research goal
    - assigned sources relevant to that section
    - specific claims tied to those sources
    - any figure placeholder slots
    - a narrow prompt for the draft pass

    This node intentionally keeps figure execution stubbed out: it creates
    placeholder metadata only, without rendering or sandbox execution.
    """
    outline = state.get("outline", {})
    registry = state.get("citation_registry", [])
    topic = state.get("topic", "")
    session_id = state.get("session_id", "")
    sections = outline.get("sections", [])

    if not sections:
        return {
            "section_contexts": [],
            "figure_slots": [],
            "current_step": "context_build",
            "status": "running",
            "steps_log": ["✓ No outline sections found for context assembly"],
        }

    section_contexts: list[dict] = []
    figure_slots: list[dict] = []
    flagged_items: list[dict] = []
    eligible_registry = [
        source for source in registry if source.get("evidence_level") != "none"
    ]
    global_hits = await semantic_search_session(
        session_id=session_id, query=topic, top_k=10
    ) if session_id and eligible_registry else []
    global_sources = _sources_from_hits(global_hits, eligible_registry)

    for index, section in enumerate(sections):
        section_name = section.get("name", f"Section {index + 1}")
        guidance = section.get("guidance") or section.get("goal") or f"Develop the {section_name} section with section-specific evidence and reasoning."
        is_synthesis = section_name.strip().lower() in _SYNTHESIS_SECTIONS
        section_hits = []
        if session_id and eligible_registry:
            section_hits = await semantic_search_session(
                session_id=session_id,
                query=f"{topic} {section_name} {guidance}",
                top_k=10,
            )
        assigned_sources = _sources_from_hits(section_hits, registry)
        if not assigned_sources:
            if global_sources:
                assigned_sources = global_sources
            elif is_synthesis:
                assigned_sources = eligible_registry[:4]
            else:
                assigned_sources = _select_relevant_sources(
                    section_name, guidance, registry
                )
        if not assigned_sources:
            flagged_items.append({
                "node": "context_build",
                "issue": f"Section {section_name} has no sources",
                "action_required": "Add or re-index relevant source material before relying on this section.",
            })

        claims = [
            {
                "claim_id": f"claim-{index + 1}-{source_index + 1}",
                "text": f"Cite {source.get('title', 'this source')} where its evidence supports a specific point in the {section_name} section.",
                "cited_chunk_ids": [source.get("id", f"source-{index + 1}-{source_index + 1}")],
                "section": section_name,
            }
            for source_index, source in enumerate(assigned_sources)
        ]

        figure_slot: dict | None = None
        if section_name.lower() not in {"conclusion", "references"}:
            figure_slot = {
                "id": f"figure-{len(figure_slots) + 1}",
                "section_name": section_name,
                "kind": "figure",
                "caption": f"{section_name} figure placeholder",
                "reason": "Placeholder reserved for future figure generation; no rendering yet.",
                "source_id": assigned_sources[0].get("id") if assigned_sources else None,
            }
            figure_slots.append(figure_slot)

        context = {
            "section_name": section_name,
            "section_goal": guidance,
            "assigned_sources": assigned_sources,
            "claims": claims,
            "figure_slots": [figure_slot] if figure_slot else [],
            "narrative_prompt": (
                f"Write a polished academic subsection for '{section_name}'. "
                f"Use the assigned sources and claims to support the argument. "
                f"Keep the section focused and evidence-based."
            ),
        }
        section_contexts.append(context)

    return {
        "section_contexts": section_contexts,
        "figure_slots": figure_slots,
        "flagged_items": flagged_items,
        "current_step": "context_build",
        "status": "running",
        "steps_log": [
            f"✓ Built section context for {len(section_contexts)} sections with {len(figure_slots)} figure placeholders"
        ],
    }
