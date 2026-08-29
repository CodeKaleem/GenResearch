# ============================================================
# Prompt: Sufficiency Evaluator
# ============================================================

SUFFICIENCY_SYSTEM = """You are GenResearch Sufficiency Evaluator. You assess whether the user's \
provided material (answers, uploaded documents, references) is sufficient to produce a well-grounded \
research paper on their topic.

This is NOT a vibe check. You evaluate against a structured rubric:

1. **Source coverage**: Does every major section/argument have at least one supporting source?
2. **Background coverage**: Is there material addressing background/context, not just the core claim?
3. **Counter-arguments**: Is there anything addressing counter-arguments or complicating evidence?
4. **Recency**: Is source recency reasonable for the topic? (e.g., AI topics need recent sources)

You MUST output valid JSON — nothing else.

Output format:
{
  "sections": {
    "<section_name>": {
      "confidence": "well_supported | adequate | weak",
      "reasoning": "Why this rating",
      "sources_found": 2,
      "sources_needed": 3
    }
  },
  "overall_assessment": "sufficient | needs_more",
  "recency_adequate": true,
  "counter_arguments_present": false,
  "summary": "One paragraph summary of the assessment"
}"""


def build_sufficiency_prompt(
    topic: str,
    answers: dict,
    available_sources: list[dict],
    retry_feedback: str = "",
) -> str:
    answers_text = "\n".join(
        f"- {k}: {v}" for k, v in answers.items()
    ) if answers else "No questionnaire answers provided."

    sources_text = "\n".join(
        f"- {s.get('title', 'Unknown')} (type: {s.get('tag', 'unknown')})"
        for s in available_sources
    ) if available_sources else "No sources available yet."

    feedback_section = ""
    if retry_feedback:
        feedback_section = f"""

IMPORTANT — PREVIOUS EVALUATION FEEDBACK:
This is your second attempt. The previous evaluation was returned because:
{retry_feedback}
Address this feedback in your new evaluation."""

    return f"""Evaluate the sufficiency of the user's material for the following research topic.

Research Topic: "{topic}"

User's Answers:
{answers_text}

Available Sources:
{sources_text}
{feedback_section}

Produce your sufficiency evaluation JSON now:"""
