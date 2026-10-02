from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

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

    for index, section in enumerate(sections):
        section_name = section.get("name", f"Section {index + 1}")
        guidance = section.get("guidance") or section.get("goal") or f"Develop the {section_name} section with section-specific evidence and reasoning."
        assigned_sources = _select_relevant_sources(section_name, guidance, registry)

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
        "current_step": "context_build",
        "status": "running",
        "steps_log": [
            f"✓ Built section context for {len(section_contexts)} sections with {len(figure_slots)} figure placeholders"
        ],
    }
