from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
        assigned_sources = list(registry[: min(3, len(registry))])

        if len(assigned_sources) == 0:
            assigned_sources = [
                {
                    "id": f"source-{index + 1}",
                    "title": f"Background source for {section_name}",
                    "abstract_snippet": "Fallback source context for the section draft.",
                }
            ]

        claims = [
            {
                "claim_id": f"claim-{index + 1}-{source_index + 1}",
                "text": f"The {section_name} section is grounded in relevant evidence from the literature.",
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
                "source_id": assigned_sources[0].get("id"),
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
