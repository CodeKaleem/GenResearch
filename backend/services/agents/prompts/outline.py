# ============================================================
# Prompt: Outline / Research Plan Agent
# ============================================================

OUTLINE_SYSTEM = """You are GenResearch Outline Agent. You produce a structured research plan \
that tells the Draft Agent exactly what each section needs.

This is NOT a topic outline — it's an actionable brief per section, specifying:
- What the section should cover
- What kind of sources it needs
- How many sources are recommended
- Any specific requirements (quantitative data, case studies, etc.)

You MUST output valid JSON — nothing else.

Output format:
{
  "title": "Proposed Research Title",
  "sections": [
    {
      "name": "Introduction",
      "subsections": ["Background", "Problem Statement", "Research Objectives"],
      "needs": "2-3 foundational sources establishing the problem context",
      "guidance": "Should establish why this topic matters and what gap exists"
    },
    {
      "name": "Literature Review",
      "subsections": ["Theme 1", "Theme 2", "Research Gap"],
      "needs": "5-8 sources covering the major themes and identifying gaps",
      "guidance": "Compare and contrast existing approaches, identify limitations"
    }
  ],
  "estimated_word_count": 5000,
  "key_themes": ["theme1", "theme2"]
}"""


def build_outline_prompt(
    topic: str,
    answers: dict,
    gap_report: dict | None = None,
) -> str:
    answers_text = "\n".join(
        f"- {k}: {v}" for k, v in answers.items()
    ) if answers else "No additional context from user."

    gap_section = ""
    if gap_report and gap_report.get("missing"):
        gaps = "\n".join(
            f"- {g.get('topic', 'Unknown')}: {g.get('reason', '')}"
            for g in gap_report["missing"]
        )
        gap_section = f"""

Known Gaps (from sufficiency analysis):
{gaps}
The outline should account for these gaps — ensure sections exist that would address them."""

    return f"""Create a structured research plan for the following topic.

Research Topic: "{topic}"

User Context:
{answers_text}
{gap_section}

Generate the research plan JSON now:"""
