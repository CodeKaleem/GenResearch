# ============================================================
# Node: Merge A+B (Join before User Approval)
# Explicitly merges outline (Branch A) + citation_registry (Branch B).
# ============================================================
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def merge_ab_node(state: dict) -> dict:
    """Validate both branches completed and merge results."""
    outline = state.get("outline")
    registry = state.get("citation_registry")

    if not outline:
        logger.warning("merge_ab: outline missing — Branch A may not have completed")
    if registry is None:
        logger.warning("merge_ab: citation_registry missing — Branch B may not have completed")

    return {
        "current_step": "merge_ab",
        "steps_log": [
            f"✓ Branches merged: outline ({len((outline or {}).get('sections', []))} sections) "
            f"+ sources ({len(registry or [])} citations)"
        ],
    }
