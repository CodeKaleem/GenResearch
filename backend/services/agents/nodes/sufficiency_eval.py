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
MIN_SOURCES_FOR_SUFFICIENT = 3


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

    # The LLM can be too lenient about coverage when the supplied source set
    # is small. Keep the override in the report itself because downstream
    # routing reads sufficiency_report.overall_assessment.
    if (
        report.get("overall_assessment") == "sufficient"
        and len(user_sources) < MIN_SOURCES_FOR_SUFFICIENT
    ):
        logger.warning(
            "sufficiency_override_insufficient_sources",
            extra={
                "user_source_count": len(user_sources),
                "min_required": MIN_SOURCES_FOR_SUFFICIENT,
            },
        )
        report["overall_assessment"] = "needs_more"
        report["summary"] = (
            f"Overridden: model judged material sufficient, but only "
            f"{len(user_sources)} source(s) were provided (minimum "
            f"{MIN_SOURCES_FOR_SUFFICIENT} required to skip the scrape-permission "
            f"step). Original assessment: {report.get('summary', '')}"
        )

    # A5 Fix: compute retry/flag locally
    passed = report.get("overall_assessment") == "sufficient"
    feedback = "Material is insufficient. Missing background or sources."
    decision = should_retry(state, NODE_NAME, passed, feedback)

    extra_state = {}
    if decision == "retry":
        extra_state = build_retry_state_update(NODE_NAME, feedback, state)
    elif decision == "flag":
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)

    return {
        "sufficiency_report": report,
        "current_step": "sufficiency_eval",
        **attempt_update,
        **extra_state,
        "steps_log": [
            f"✓ Sufficiency evaluation: {report.get('overall_assessment', 'unknown')}"
        ],
    }
