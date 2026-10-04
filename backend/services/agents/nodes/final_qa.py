# ============================================================
# Node: Final QA (Stage 13)
# Whole-paper check — only meaningful after both C and D complete.
# Model: nemotron-3-nano
#
# A5: Retry/flag state is now written INSIDE the node, not in
#     the routing function (which can only select the next node).
# ============================================================
from __future__ import annotations
import logging

from config import settings
from services.llm_service import call_llm
from services.agents.prompts.final_qa import (
    FINAL_QA_SYSTEM, FINAL_QA_THRESHOLD, build_final_qa_prompt,
)
from services.agents.retry import (
    get_attempt_count,
    increment_attempt, should_retry,
    build_retry_state_update, build_flag_state_update,
)
from services.agents.json_utils import coerce_score, parse_llm_json

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
        context_limit=settings.OLLAMA_JUDGE_CONTEXT,
    )

    result = parse_llm_json(raw)
    score = coerce_score(result.get("overall_score")) if result else None
    unknown = result is None or score is None
    attempts_done = get_attempt_count(state, NODE_NAME) + 1
    if result is None:
        result = {}
    if unknown:
        result.update({
            "overall_score": None,
            "unknown": True,
            "passed": attempts_done >= 2,
            "summary": "Final QA response was not parseable or had no valid score.",
            "issues": result.get("issues") or [],
        })
    else:
        result["overall_score"] = score
        result["passed"] = score >= FINAL_QA_THRESHOLD

    # A5: Compute retry/flag decision and write state HERE, not in router
    passed = result["passed"]
    feedback = "\n".join(str(i) for i in result.get("issues", []))
    if unknown and attempts_done == 1:
        feedback = "Final QA returned an unknown result; retry evaluation once."
    decision = should_retry(
        state,
        NODE_NAME,
        passed,
        feedback,
        attempts_done=attempts_done,
    )

    extra_state = {}
    if unknown and attempts_done >= 2:
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)
    elif decision == "retry":
        extra_state = build_retry_state_update(NODE_NAME, feedback, state)
    elif decision == "flag":
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)

    score_label = f"{score:g}" if score is not None else "unknown"
    return {
        "final_qa_result": result,
        "current_step": "final_qa",
        **attempt_update,
        **extra_state,
        "steps_log": [
            f"✓ Final QA: {score_label}/10 "
            f"({'PASSED' if result['passed'] else 'NEEDS REVIEW'})"
        ],
    }
