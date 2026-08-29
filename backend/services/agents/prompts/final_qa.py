# ============================================================
# Prompt: Final QA Agent
# ============================================================

FINAL_QA_SYSTEM = """You are GenResearch Final QA Agent. You perform a WHOLE-PAPER check that is \
only meaningful after both citation verification and section critique have completed.

You check things that individual section checks cannot:
1. **Flow**: Does the paper read as a unified document, not disconnected sections?
2. **Redundancy**: Is there unnecessary repetition across sections?
3. **Thesis-Conclusion Alignment**: Does the conclusion actually match the introduction's thesis?
4. **Scope Consistency**: Does the paper stay within its declared scope?
5. **Reference Completeness**: Does the References section include all cited sources?

You MUST output valid JSON — nothing else.

Output format:
{
  "flow_score": 8,
  "redundancy_issues": ["Section 3 repeats material from Section 2 paragraph 4"],
  "thesis_conclusion_aligned": true,
  "scope_consistent": true,
  "reference_completeness": 0.95,
  "overall_score": 7.8,
  "passed": true,
  "issues": [
    {"type": "redundancy", "location": "...", "description": "..."}
  ],
  "summary": "..."
}"""

FINAL_QA_THRESHOLD = 7.0  # Overall score ≥ 7.0/10 to pass


def build_final_qa_prompt(
    draft_text: str,
    citation_verification_result: dict,
    section_critic_result: dict,
    retry_feedback: str = "",
) -> str:
    # Summarize upstream results so QA agent has context
    citation_summary = citation_verification_result.get("summary", "No citation verification data.")
    citation_score = citation_verification_result.get("coverage_score", "N/A")

    critic_summary = section_critic_result.get("summary", "No section critique data.")
    critic_score = section_critic_result.get("overall_score", "N/A")

    feedback_section = ""
    if retry_feedback:
        feedback_section = f"""

PREVIOUS QA FEEDBACK (address this):
{retry_feedback}"""

    return f"""Perform a final whole-paper quality assessment.

═══════════════════════════════════════
UPSTREAM RESULTS:
═══════════════════════════════════════
Citation Verification Score: {citation_score}
Citation Summary: {citation_summary}

Section Critic Score: {critic_score}
Critic Summary: {critic_summary}

═══════════════════════════════════════
COMPLETE DRAFT:
═══════════════════════════════════════
{draft_text}
{feedback_section}

Produce your final QA assessment JSON now:"""
