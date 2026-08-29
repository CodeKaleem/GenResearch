# ============================================================
# Node: Outline / Research Plan Agent (Stage 5 — Branch A)
# Runs CONCURRENTLY with Branch B (Source Gathering).
# Only depends on Topic + Questionnaire answers, NOT on sources.
# Model: nemotron-3-nano
# Writes to: state.outline (Branch B writes to different keys)
# ============================================================
from __future__ import annotations

import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.outline import (
    OUTLINE_SYSTEM,
    build_outline_prompt,
)

logger = logging.getLogger(__name__)


async def outline_plan_node(state: dict) -> dict:
    """
    Branch A (Stage 5): Generate structured research plan.
    Per-section brief with source needs and guidance.
    """
    topic = state["topic"]
    answers = state.get("questionnaire_answers", {})
    gap_report = state.get("gap_report")

    prompt = build_outline_prompt(
        topic=topic,
        answers=answers,
        gap_report=gap_report,
    )

    raw = await call_llm(
        prompt=prompt,
        agent_role="outline_plan",
        system=OUTLINE_SYSTEM,
        temperature=0.3,
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
        outline_data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("outline_json_parse_failed", extra={"raw": raw[:500]})
        # Fallback: basic academic structure
        outline_data = {
            "title": topic,
            "sections": [
                {"name": "Introduction", "subsections": ["Background", "Problem Statement", "Objectives"], "needs": "2-3 foundational sources", "guidance": "Establish context and research gap"},
                {"name": "Literature Review", "subsections": ["Key Themes", "Research Gap"], "needs": "5-8 relevant sources", "guidance": "Synthesize existing work"},
                {"name": "Methodology", "subsections": ["Research Design", "Data Collection"], "needs": "2-3 methodological references", "guidance": "Be specific and replicable"},
                {"name": "Results and Discussion", "subsections": ["Expected Findings"], "needs": "Support with cited evidence", "guidance": "Connect to research objectives"},
                {"name": "Conclusion", "subsections": ["Summary", "Future Work"], "needs": "Tie back to introduction", "guidance": "Highlight contributions"},
            ],
            "estimated_word_count": 5000,
            "key_themes": [],
        }

    num_sections = len(outline_data.get("sections", []))

    return {
        "outline": outline_data,
        "current_step": "outline_plan",
        "steps_log": [
            f"✓ Research outline generated: {num_sections} sections planned"
        ],
    }
