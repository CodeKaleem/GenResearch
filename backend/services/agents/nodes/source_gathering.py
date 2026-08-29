# ============================================================
# Node: Source Gathering (Stage 6 — Branch B, Step 1)
# Gap-driven retrieval — no LLM call, this is a tool/fetch node.
# Writes to: state.scraped_sources (Branch A writes to state.outline)
# ============================================================
from __future__ import annotations

import logging

from services.source_gathering import gather_sources_for_gaps

logger = logging.getLogger(__name__)


async def source_gathering_node(state: dict) -> dict:
    """
    Branch B, Step 1 (Stage 6): Fetch academic sources for identified gaps.
    If the user already provided links, those are ingested directly (they're
    already in state.user_provided_sources from the questionnaire stage).
    """
    gap_report = state.get("gap_report", {})
    gaps = gap_report.get("missing", [])
    existing = state.get("user_provided_sources", [])

    if not gaps:
        # No gaps — everything is covered by user's material
        return {
            "scraped_sources": [],
            "current_step": "source_gathering",
            "steps_log": [
                "✓ No source gaps — user's material is sufficient"
            ],
        }

    found_sources, unfilled_gaps = await gather_sources_for_gaps(
        gaps=gaps,
        existing_sources=existing,
        sources_per_gap=3,
    )

    # Flag unfilled gaps so they appear in the Completion Guide
    new_flags = []
    for gap in unfilled_gaps:
        new_flags.append({
            "node": "source_gathering",
            "issue": f"Could not find sources for: {gap.get('topic', 'Unknown')}. "
                     f"Reason: {gap.get('reason', 'No results from academic APIs.')}",
            "attempts": 1,
            "action_required": "You may need to find sources for this topic manually.",
        })

    return {
        "scraped_sources": found_sources,
        "flagged_items": new_flags,
        "current_step": "source_gathering",
        "steps_log": [
            f"✓ Found {len(found_sources)} academic sources for {len(gaps)} gaps"
            + (f" ({len(unfilled_gaps)} gaps still unfilled)" if unfilled_gaps else "")
        ],
    }
