# ============================================================
# GenResearch — Retry & Flagging Logic
# Shared by all correction-capable nodes.
#
# Rules (spec §6, non-negotiable):
#   - Maximum 2 attempts per node, then flag to user.
#   - Every loop-back carries STRUCTURED feedback, not a bare "redo".
#   - Pass/fail thresholds are concrete and scorable.
#   - A flagged item NEVER halts the pipeline — it's surfaced
#     in the Completion Guide and the pipeline continues.
# ============================================================
from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def get_attempt_count(state: dict, node_name: str) -> int:
    """How many times has this node been attempted so far?"""
    counts = state.get("retry_counts", {})
    return counts.get(node_name, 0)


def increment_attempt(state: dict, node_name: str) -> dict:
    """
    Increment the attempt counter for a node.
    Returns a state-update dict (not the full state).
    With _merge_dicts reducer, we only need to return the changed key.
    """
    current = state.get("retry_counts", {}).get(node_name, 0)
    return {"retry_counts": {node_name: current + 1}}


def should_retry(
    state: dict,
    node_name: str,
    passed: bool,
    feedback: str,
) -> Literal["proceed", "retry", "flag"]:
    """
    Decide what to do after a node's evaluation pass.

    Args:
        state:     Current pipeline state.
        node_name: Name of the node being evaluated.
        passed:    Whether the evaluation passed its concrete threshold.
        feedback:  Structured explanation of WHY it failed (if it did).

    Returns:
        "proceed" — evaluation passed, continue downstream.
        "retry"   — evaluation failed, attempt count < MAX_RETRIES, loop back.
        "flag"    — evaluation failed AND attempts exhausted. Flag for user.
    """
    if passed:
        return "proceed"

    attempt = get_attempt_count(state, node_name)

    if attempt < MAX_RETRIES:
        logger.info(
            "retry_triggered",
            extra={
                "node": node_name,
                "attempt": attempt + 1,
                "max": MAX_RETRIES,
                "feedback": feedback[:200],
            },
        )
        return "retry"

    logger.warning(
        "retry_cap_reached",
        extra={
            "node": node_name,
            "attempts": attempt,
            "feedback": feedback[:200],
        },
    )
    return "flag"


def build_retry_state_update(
    node_name: str,
    feedback: str,
    current_state: dict,
) -> dict:
    """
    Build the state-update dict for a retry loop-back.
    Increments the attempt counter and stores structured feedback.
    With _merge_dicts reducer, only return the changed keys.
    """
    current = current_state.get("retry_counts", {}).get(node_name, 0)

    return {
        "retry_counts": {node_name: current + 1},
        "retry_feedback": {node_name: feedback},
    }


def build_flag_state_update(
    node_name: str,
    feedback: str,
    current_state: dict,
) -> dict:
    """
    Build the state-update dict when a node hits the retry cap.
    Adds the issue to flagged_items for the Completion Guide.
    The pipeline CONTINUES — a flagged item never halts the run.
    With operator.add reducer, only return the NEW items to append.
    """
    return {"flagged_items": [{
        "node": node_name,
        "issue": feedback,
        "attempts": get_attempt_count(current_state, node_name),
        "action_required": "Needs your review — automated correction was insufficient.",
    }]}
