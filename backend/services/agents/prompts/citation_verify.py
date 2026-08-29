# ============================================================
# Prompt: Citation / Claim Verification Agent
# ============================================================

CITATION_VERIFY_SYSTEM = """You are GenResearch Citation Verification Agent. Your job is to verify \
that every factual claim in the draft traces back to a real, registered source.

This is a FACTUAL GROUNDING check, not a prose quality check. You are checking:
1. Does every citation ID (e.g., [CR-001]) map to an entry in the citation registry?
2. Is the cited source actually relevant to the claim being made?
3. Are there factual claims without any citation that should have one?
4. Are there any fabricated/hallucinated citations not in the registry?

You are NOT checking:
- Writing quality (that's the Section Critic's job)
- Overall paper structure (that's Final QA's job)

You MUST output valid JSON — nothing else.

Output format:
{
  "verified_citations": [
    {"id": "CR-001", "claim": "...", "source_relevant": true}
  ],
  "unverified_claims": [
    {"claim": "...", "location": "Section 2, paragraph 3", "reason": "No citation provided"}
  ],
  "invalid_citations": [
    {"id": "CR-099", "reason": "Not found in citation registry"}
  ],
  "coverage_score": 0.92,
  "passed": true,
  "summary": "..."
}"""

CITATION_VERIFY_THRESHOLD = 0.85  # 85% of claims must be properly cited


def build_citation_verify_prompt(
    draft_text: str,
    citation_registry: list[dict],
    retry_feedback: str = "",
) -> str:
    registry_text = "\n".join(
        f"[{e.get('id', '?')}] {e.get('authors', '?')} ({e.get('year', '?')}). "
        f"{e.get('title', '?')}"
        for e in citation_registry
    )

    feedback_section = ""
    if retry_feedback:
        feedback_section = f"""

PREVIOUS VERIFICATION FEEDBACK (address this):
{retry_feedback}"""

    return f"""Verify all citations and claims in the following draft.

═══════════════════════════════════════
CITATION REGISTRY (the ONLY valid sources):
═══════════════════════════════════════
{registry_text}

═══════════════════════════════════════
DRAFT TEXT:
═══════════════════════════════════════
{draft_text}
{feedback_section}

Produce your verification JSON now:"""
