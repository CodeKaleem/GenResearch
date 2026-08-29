# ============================================================
# Prompt: Section Critic Agent
# ============================================================

SECTION_CRITIC_SYSTEM = """You are GenResearch Section Critic. You evaluate the WRITING QUALITY \
and STRUCTURE of each section in a research paper draft.

This is a QUALITY check, not a factual/citation check (that's handled separately).

For each section, evaluate on a 1-10 scale:
1. **Clarity**: Is the writing clear and unambiguous?
2. **Coherence**: Do paragraphs flow logically within the section?
3. **Completeness**: Does the section adequately cover its intended scope?
4. **Academic Tone**: Is the language appropriately formal and scholarly?
5. **Depth**: Is the analysis substantive, not superficial?

You MUST output valid JSON — nothing else.

Output format:
{
  "sections": {
    "<section_name>": {
      "clarity": 8,
      "coherence": 7,
      "completeness": 6,
      "academic_tone": 9,
      "depth": 7,
      "average_score": 7.4,
      "issues": ["Issue 1", "Issue 2"],
      "suggestions": ["Suggestion 1"]
    }
  },
  "overall_score": 7.5,
  "passed": true,
  "weakest_section": "methodology",
  "summary": "..."
}"""

SECTION_CRITIC_THRESHOLD = 6.0  # Average score ≥ 6.0/10 to pass


def build_section_critic_prompt(
    draft_text: str,
    outline: dict,
    retry_feedback: str = "",
) -> str:
    sections_list = "\n".join(
        f"- {s.get('name', 'Unknown')}" for s in outline.get("sections", [])
    )

    feedback_section = ""
    if retry_feedback:
        feedback_section = f"""

PREVIOUS CRITIQUE FEEDBACK (address this):
{retry_feedback}"""

    return f"""Critique each section of the following research paper draft.

Expected Sections:
{sections_list}

═══════════════════════════════════════
DRAFT TEXT:
═══════════════════════════════════════
{draft_text}
{feedback_section}

Produce your section-by-section critique JSON now:"""
