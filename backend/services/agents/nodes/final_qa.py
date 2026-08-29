# ============================================================
# Node: Final QA (Stage 13)
# Whole-paper check — only meaningful after both C and D complete.
# Model: nemotron-3-nano
# ============================================================
from __future__ import annotations
import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.final_qa import (
    FINAL_QA_SYSTEM, FINAL_QA_THRESHOLD, build_final_qa_prompt,
)
from services.agents.retry import increment_attempt

logger = logging.getLogger(__name__)
NODE_NAME = "final_qa"


async def final_qa_node(state: dict) -> dict:
    draft = state.get("draft_text", "")
    cv_result = state.get("citation_verification_result", {})
    sc_result = state.get("section_critic_result", {})
    retry_fb = state.get("retry_feedback", {}).get(NODE_NAME, "")
    attempt_update = increment_attempt(state, NODE_NAME)

    prompt = build_final_qa_prompt(draft, cv_result, sc_result, retry_fb)

    raw = await call_llm(
        prompt=prompt, agent_role="final_qa",
        system=FINAL_QA_SYSTEM, temperature=0.2, max_tokens=2000,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {"overall_score": 0, "passed": False,
                  "summary": "Failed to parse QA output.", "issues": []}

    score = result.get("overall_score", 0)
    result["passed"] = score >= FINAL_QA_THRESHOLD

    return {
        "final_qa_result": result,
        "current_step": "final_qa",
        **attempt_update,
        "steps_log": [
            f"✓ Final QA: {score}/10 "
            f"({'PASSED' if result['passed'] else 'NEEDS REVIEW'})"
        ],
    }
