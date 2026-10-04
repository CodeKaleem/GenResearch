# ============================================================
# Node: Citation/Claim Verification (Stage 11 — Branch C)
# MUST run on nemotron-3-nano (different from Draft Agent's model).
#
# A5: Retry/flag state is now written INSIDE the node, not in
#     the routing function (which can only select the next node).
# ============================================================
from __future__ import annotations
import logging

from config import settings
from services.llm_service import call_llm
from services.agents.prompts.citation_verify import (
    CITATION_VERIFY_SYSTEM, CITATION_VERIFY_THRESHOLD, build_citation_verify_prompt,
)
from services.agents.retry import (
    get_attempt_count, increment_attempt, should_retry,
    build_retry_state_update, build_flag_state_update,
)
from services.agents.json_utils import coerce_score, parse_llm_json

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
        context_limit=settings.OLLAMA_JUDGE_CONTEXT,
    )

    parsed = parse_llm_json(raw)
    score = coerce_score(parsed.get("coverage_score"), percentage=True) if parsed else None
    unknown = parsed is None or score is None
    attempts_done = get_attempt_count(state, NODE_NAME) + 1
    unverified_claims = parsed.get("unverified_claims", []) if parsed else []
    if not isinstance(unverified_claims, list):
        unverified_claims = []
    result = parsed or {}
    if unknown:
        result.update({
            "coverage_score": None,
            "unknown": True,
            "summary": "Verification response was not parseable or had no valid score.",
            "unverified_claims": unverified_claims,
        })
        result["passed"] = attempts_done >= 2
    else:
        result["coverage_score"] = score
        result["passed"] = score >= CITATION_VERIFY_THRESHOLD

    generated_sections = state.get("generated_sections", [])
    failed_sections = set()
    for issue in unverified_claims:
        if not isinstance(issue, dict):
            continue
        claim = str(issue.get("claim", "")).strip().lower()
        location = str(issue.get("location", "")).lower()
        for section in generated_sections:
            name = str(section.get("section_name", ""))
            if name and (
                name.lower() in location
                or (claim and claim in str(section.get("text", "")).lower())
            ):
                failed_sections.add(name)

    # A5: Compute retry/flag decision and write state HERE, not in router
    passed = result["passed"]
    feedback = "\n".join(
        str(issue.get("claim", ""))
        for issue in unverified_claims
        if isinstance(issue, dict)
    )
    if unknown and attempts_done == 1:
        feedback = "The citation verifier returned an unknown result; retry verification once."
    decision = should_retry(
        state, NODE_NAME, passed, feedback, attempts_done=attempts_done
    )
    result["retry_sections"] = sorted(failed_sections) if decision == "retry" else []

    extra_state = {}
    if unknown and attempts_done >= 2:
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)
    elif decision == "retry":
        extra_state = build_retry_state_update(NODE_NAME, feedback, state)
    elif decision == "flag":
        extra_state = build_flag_state_update(NODE_NAME, feedback, state)

    score_label = f"{score:.0%}" if score is not None else "unknown"

    return {
        "citation_verification_result": result,
        "current_step": "citation_verification",
        **attempt_update,
        **extra_state,
        "steps_log": [
            f"✓ Citation verification: {score_label} coverage "
            f"({'PASSED' if result['passed'] else 'NEEDS REVIEW'})"
        ],
    }
