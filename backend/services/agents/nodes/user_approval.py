# ============================================================
# Node: User Approval (Stage 9 — Human-in-the-Loop Checkpoint)
# The pipeline PAUSES here until the user approves.
# ============================================================
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def user_approval_node(state: dict) -> dict:
    """
    Stage 9: Human-in-the-loop checkpoint.
    The user sees the approved outline + gathered sources before
    expensive draft generation happens.

    In LangGraph, this node's output sets status to 'awaiting_approval'.
    The actual interrupt is handled by the graph's interrupt_before
    configuration on this node. The pipeline API resumes execution
    when the user submits their approval.
    """
    return {
        "status": "awaiting_approval",
        "current_step": "user_approval",
        "steps_log": [
            "⏸ Awaiting your approval of the outline and sources before drafting"
        ],
    }
