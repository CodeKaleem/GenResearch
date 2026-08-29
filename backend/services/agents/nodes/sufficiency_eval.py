# ============================================================
# Node: Sufficiency Evaluator (Stage 3)
# Rubric-based evaluation with retry support (max 2 attempts).
# Model: nemotron-3-nano
# ============================================================
from __future__ import annotations

import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.sufficiency import (
    SUFFICIENCY_SYSTEM,
    build_sufficiency_prompt,
)
from services.agents.retry import (
    increment_attempt,
    should_retry,
    build_retry_state_update,
    build_flag_state_update,
)

logger = logging.getLogger(__name__)

NODE_NAME = "sufficiency_eval"


async def sufficiency_eval_node(state: dict) -> dict:
    """
    Stage 3: Evaluate sufficiency of user's provided material.
    Per-section confidence scoring with structured rubric.
    Supports retry loop (max 2) with structured feedback.
    """
    topic = state["topic"]
    answers = state.get("questionnaire_answers", {})
    user_sources = state.get("user_provided_sources", [])
    retry_fb = state.get("retry_feedback", {}).get(NODE_NAME, "")

    # Track attempt
    attempt_update = increment_attempt(state, NODE_NAME)

    prompt = build_sufficiency_prompt(
        topic=topic,
        answers=answers,
        available_sources=user_sources,
        retry_feedback=retry_fb,
    )

    raw = await call_llm(
        prompt=prompt,
        agent_role="sufficiency_evaluator",
        system=SUFFICIENCY_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
    )

    # Parse JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    try:
        report = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("sufficiency_json_parse_failed", extra={"raw": raw[:500]})
        report = {
            "sections": {},
            "overall_assessment": "needs_more",
            "summary": "Failed to parse evaluation — treating as needs_more.",
        }

    return {
        "sufficiency_report": report,
        "current_step": "sufficiency_eval",
        **attempt_update,
        "steps_log": [
            f"✓ Sufficiency evaluation: {report.get('overall_assessment', 'unknown')}"
        ],
    }
