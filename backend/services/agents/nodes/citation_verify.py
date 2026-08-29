# ============================================================
# Node: Citation/Claim Verification (Stage 11 — Branch C)
# MUST run on nemotron-3-nano (different from Draft Agent's model).
#
# A5: Retry/flag state is now written INSIDE the node, not in
#     the routing function (which can only select the next node).
# ============================================================
from __future__ import annotations
import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.citation_verify import (
    CITATION_VERIFY_SYSTEM, CITATION_VERIFY_THRESHOLD, build_citation_verify_prompt,
)
from services.agents.retry import (
    increment_attempt, should_retry,
    build_retry_state_update, build_flag_state_update,
)

logger = logging.getLogger(__name__)
NODE_NAME = "citation_verification"


async def citation_verify_node(state: dict) -> dict:
    draft = state.get("draft_text", "")
    registry = state.get("citation_registry", [])
    retry_fb = state.get("retry_feedback", {}).get(NODE_NAME, "")
    attempt_update = increment_attempt(state, NODE_NAME)

    prompt = build_citation_verify_prompt(draft, registry, retry_fb)

    raw = await call_llm(
        prompt=prompt, agent_role="citation_verification",
        system=CITATION_VERIFY_SYSTEM, temperature=0.1, max_tokens=2000,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {"coverage_score": 0, "passed": False,
                  "summary": "Failed to parse verification output.", "unverified_claims": []}

    # Apply concrete threshold
    score = result.get("coverage_score", 0)
    result["passed"] = score >= CITATION_VERIFY_THRESHOLD

    # A5: Compute retry/flag decision and write state HERE, not in router
    passed = result["passed"]
    feedback = "\n".join(c.get("claim", "") for c in result.get("unverified_claims", []))
    decision = should_retry(state, NODE_NAME, passed, feedback)

    extra_state = {}
    if decision == "retry":
        extra_state = build_retry_state_update(NODE_NAME, feedback, state)
    elif decision == "flag":
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)

    return {
        "citation_verification_result": result,
        "current_step": "citation_verification",
        **attempt_update,
        **extra_state,
        "steps_log": [
            f"✓ Citation verification: {score:.0%} coverage "
            f"({'PASSED' if result['passed'] else 'NEEDS REVIEW'})"
        ],
    }
