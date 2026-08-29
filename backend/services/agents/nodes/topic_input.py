# ============================================================
# Node: Topic Input (Stage 1)
# Validation only — no LLM call.
# ============================================================
from __future__ import annotations

import uuid
import logging

logger = logging.getLogger(__name__)


async def topic_input_node(state: dict) -> dict:
    """
    Stage 1: Validate and normalize the user's topic input.
    No LLM call — this is pure validation.
    """
    topic = state.get("topic", "").strip()
    if not topic:
        raise ValueError("Research topic cannot be empty.")

    session_id = state.get("session_id") or str(uuid.uuid4())
    citation_style = state.get("citation_style", "apa").lower()

    if citation_style not in ("apa", "ieee", "mla", "chicago"):
        citation_style = "apa"

    logger.info("topic_input", extra={"topic": topic[:100], "session_id": session_id})

    return {
        "topic": topic,
        "session_id": session_id,
        "citation_style": citation_style,
        "status": "running",
        "current_step": "topic_input",
        "retry_counts": {},
        "retry_feedback": {},
        "flagged_items": [],
        "steps_log": [
            f"✓ Topic accepted: \"{topic[:80]}{'…' if len(topic) > 80 else ''}\""
        ],
    }
