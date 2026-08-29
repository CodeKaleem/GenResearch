# ============================================================
# Node: Section Critic (Stage 12 — Branch D)
# Model: nemotron-3-nano
# ============================================================
from __future__ import annotations
import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.section_critic import (
    SECTION_CRITIC_SYSTEM, SECTION_CRITIC_THRESHOLD, build_section_critic_prompt,
)
from services.agents.retry import increment_attempt

logger = logging.getLogger(__name__)
NODE_NAME = "section_critic"


async def section_critic_node(state: dict) -> dict:
    draft = state.get("draft_text", "")
    outline = state.get("outline", {})
    retry_fb = state.get("retry_feedback", {}).get(NODE_NAME, "")
    attempt_update = increment_attempt(state, NODE_NAME)

    prompt = build_section_critic_prompt(draft, outline, retry_fb)

    raw = await call_llm(
        prompt=prompt, agent_role="section_critic",
        system=SECTION_CRITIC_SYSTEM, temperature=0.2, max_tokens=2000,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {"overall_score": 0, "passed": False, "sections": {},
                  "summary": "Failed to parse critique output."}

    score = result.get("overall_score", 0)
    result["passed"] = score >= SECTION_CRITIC_THRESHOLD

    return {
        "section_critic_result": result,
        "current_step": "section_critic",
        **attempt_update,
        "steps_log": [
            f"✓ Section critique: {score}/10 overall "
            f"({'PASSED' if result['passed'] else 'NEEDS REVIEW'})"
        ],
    }
