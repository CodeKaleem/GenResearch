# ============================================================
# Node: Gap Report (Stage 4)
# Transforms sufficiency report into actionable gap list.
# Model: nemotron-3-nano
# ============================================================
from __future__ import annotations

import json
import logging

from services.llm_service import call_llm

logger = logging.getLogger(__name__)

GAP_REPORT_SYSTEM = """You are GenResearch Gap Report Agent. You transform a sufficiency evaluation \
into a concrete, actionable gap report that tells the Source Gathering stage exactly what to look for.

Rules:
1. "covered" items are topics/sections with adequate source support — no action needed.
2. "missing" items are specific gaps that need sources. Each must have:
   - topic: What specific thing needs a source
   - reason: Why it's a gap (from the sufficiency report)
   - search_query: A concrete search query to find relevant academic sources
3. Be specific: "find a source addressing counter-arguments to transformer efficiency" \
   is correct. "find 5 sources" is WRONG — gap-driven, not quota-driven.

You MUST output valid JSON — nothing else.

Output format:
{
  "covered": [
    {"section": "Introduction", "topic": "Problem context", "confidence": "well_supported"}
  ],
  "missing": [
    {
      "section": "Literature Review",
      "topic": "Counter-arguments to the main thesis",
      "reason": "No sources address opposing viewpoints",
      "search_query": "limitations criticisms of [specific approach]",
      "priority": "high"
    }
  ]
}"""


async def gap_report_node(state: dict) -> dict:
    """
    Stage 4: Convert sufficiency report into structured gap report.
    This becomes the exact brief for the Source Gathering branch.
    """
    topic = state["topic"]
    sufficiency = state.get("sufficiency_report", {})

    # Build a textual summary of the sufficiency report for the LLM
    sections_text = ""
    for section_name, data in sufficiency.get("sections", {}).items():
        conf = data.get("confidence", "unknown") if isinstance(data, dict) else data
        reasoning = data.get("reasoning", "") if isinstance(data, dict) else ""
        sections_text += f"- {section_name}: {conf}"
        if reasoning:
            sections_text += f" — {reasoning}"
        sections_text += "\n"

    prompt = f"""Analyze the following sufficiency evaluation and produce an actionable gap report.

Research Topic: "{topic}"

Sufficiency Report:
{sections_text}

Overall Assessment: {sufficiency.get('overall_assessment', 'unknown')}
Summary: {sufficiency.get('summary', 'No summary available.')}

Produce the gap report JSON now:"""

    raw = await call_llm(
        prompt=prompt,
        agent_role="gap_report",
        system=GAP_REPORT_SYSTEM,
        temperature=0.2,
        max_tokens=2000,
    )

    # Parse JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    try:
        gap_data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("gap_report_json_parse_failed", extra={"raw": raw[:500]})
        gap_data = {
            "covered": [],
            "missing": [
                {
                    "section": "General",
                    "topic": topic,
                    "reason": "Unable to parse gap analysis — performing general source search.",
                    "search_query": topic,
                    "priority": "high",
                }
            ],
        }

    return {
        "gap_report": gap_data,
        "current_step": "gap_report",
        "steps_log": [
            f"✓ Gap report: {len(gap_data.get('covered', []))} covered, "
            f"{len(gap_data.get('missing', []))} gaps identified"
        ],
    }
