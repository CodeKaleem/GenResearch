# ============================================================
# Node: Scrape Permission (Stage 3b — B3)
# Human-in-the-loop checkpoint before external scraping.
# Only triggered if sufficiency_eval returns 'needs_more'.
# ============================================================
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def scrape_permission_node(state: dict) -> dict:
    """
    Stage 3b (B3): Human-in-the-loop checkpoint.
    The pipeline PAUSES here to ask if it should scrape the web for more sources.
    This only runs if the sufficiency report indicated material is insufficient.

    In LangGraph, this node sets status to 'awaiting_scrape_permission'.
    The interrupt is handled by the graph's interrupt_before configuration.
    """
    result = {
        "status": "awaiting_scrape_permission",
        "current_step": "scrape_permission",
        "steps_log": [
            "⏸ Insufficient material — awaiting permission to search for external sources"
        ],
    }
    if not state.get("scrape_permission_granted", False):
        result["flagged_items"] = [{
            "node": "scrape_permission",
            "issue": "Scraping denied by user despite insufficient material.",
            "attempts": 1,
            "action_required": "Consider allowing scraping if draft quality is poor.",
        }]
    return result
