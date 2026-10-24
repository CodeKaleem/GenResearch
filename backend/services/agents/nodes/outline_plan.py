# ============================================================
# Node: Outline / Research Plan Agent (Stage 5 — Branch A)
# Runs CONCURRENTLY with Branch B (Source Gathering).
# Only depends on Topic + Questionnaire answers, NOT on sources.
# Model: nemotron-3-nano
# Writes to: state.outline (Branch B writes to different keys)
# ============================================================
from __future__ import annotations

import logging
import time

from services.llm_service import call_llm
from services.agents.prompts.outline import (
    OUTLINE_SYSTEM,
    build_outline_prompt,
)
from services.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)


async def outline_plan_node(state: dict) -> dict:
    """
    Branch A (Stage 5): Generate structured research plan.
    Per-section brief with source needs and guidance.
    """
    started_at = time.perf_counter()
    logger.info("outline_plan_started", extra={"request_count": 1})
    topic = state["topic"]
    answers = state.get("questionnaire_answers", {})
    gap_report = state.get("gap_report")

    prompt = build_outline_prompt(
        topic=topic,
        answers=answers,
        gap_report=gap_report,
    )

    raw = await call_llm(
        prompt=prompt,
        agent_role="outline_plan",
        system=OUTLINE_SYSTEM,
        temperature=0.3,
        max_tokens=4000,
    )

    outline_data = parse_llm_json(raw)
    parse_failed = outline_data is None
    if parse_failed:
        logger.warning("outline_json_parse_failed", extra={"raw": raw[:500]})
        # Fallback: basic academic structure
        outline_data = {
            "title": topic,
            "abstract_required": True,
            "sections": [
                {
                    "name": "Abstract",
                    "subsections": ["Problem Summary", "Method Summary", "Key Findings", "Contribution"],
                    "needs": "Synthesized from the full paper",
                    "guidance": "150-300 words. Cover: problem, method, key findings, contribution. No citations.",
                    "word_count_target": 250,
                },
                {
                    "name": "Introduction",
                    "subsections": [
                        "Background of the Study",
                        "Research Context",
                        "Problem Statement",
                        "Research Gap",
                        "Aim of the Study",
                        "Research Objectives",
                        "Research Questions",
                        "Significance of the Study",
                        "Scope and Delimitations",
                        "Organization of the Paper",
                    ],
                    "needs": "2-4 foundational sources establishing the research context and supporting the problem statement",
                    "guidance": "Follow order: background → context → problem → gap → aim → objectives → RQs → significance → scope → organization. Research gap must emerge from evidence, not assertion.",
                    "word_count_target": 800,
                },
                {
                    "name": "Literature Review",
                    "subsections": [
                        "Introduction to the Literature Review",
                        "Definition of Key Concepts",
                        "Theoretical Foundations",
                        "Review of Previous Studies (by Theme)",
                        "Critical Comparison of Studies",
                        "Research Gap Identification",
                        "Summary of Literature",
                    ],
                    "needs": "6-10 peer-reviewed sources organized by theme",
                    "guidance": "Organize by THEMES not by paper. Compare methodologies. Identify contradictions. Gap must be specific and evidenced.",
                    "word_count_target": 1500,
                },
                {
                    "name": "Theoretical Framework",
                    "subsections": [
                        "Selected Theory or Model",
                        "Key Concepts",
                        "Relevance to Research Problem",
                        "Application in Previous Studies",
                        "How it Guides This Investigation",
                    ],
                    "needs": "1-3 foundational theory sources",
                    "guidance": "Only include if the study uses an established theory. Justify the theory choice. Omit this section if no theoretical framework applies.",
                    "word_count_target": 400,
                },
                {
                    "name": "Research Methodology",
                    "subsections": [
                        "Research Approach",
                        "Research Design",
                        "Research Setting and Context",
                        "Data Sources and Collection",
                        "Data Analysis Procedure",
                        "Ethical Considerations",
                        "Limitations of Methodology",
                    ],
                    "needs": "2-4 methodological references justifying the approach",
                    "guidance": "Be specific and replicable. State approach, design, context, data sources, analysis procedure. Justify every choice.",
                    "word_count_target": 800,
                },
                {
                    "name": "Results",
                    "subsections": [
                        "Overview of Findings",
                        "Quantitative Results",
                        "Qualitative Findings",
                        "Summary Tables and Figures",
                    ],
                    "needs": "Empirical data from the study",
                    "guidance": "Report findings ONLY — no interpretation. Use tables/figures with numbered captions. Organize by research question.",
                    "word_count_target": 600,
                },
                {
                    "name": "Discussion",
                    "subsections": [
                        "Interpretation of Findings",
                        "Comparison with Prior Literature",
                        "Theoretical Implications",
                        "Practical Implications",
                    ],
                    "needs": "Sources from Literature Review to compare findings against",
                    "guidance": "Interpret results, compare to literature, explain implications. Do NOT repeat raw results. Link each interpretation to a result AND a source.",
                    "word_count_target": 700,
                },
                {
                    "name": "Limitations",
                    "subsections": [
                        "Study Limitations",
                        "Impact on Conclusions",
                        "Threats to Validity",
                    ],
                    "needs": "Honest acknowledgment from the methodology and results",
                    "guidance": "Acknowledge all significant constraints. Explain how limitations affect conclusions. Do not minimize.",
                    "word_count_target": 300,
                },
                {
                    "name": "Conclusion",
                    "subsections": [
                        "Summary of the Study",
                        "Answers to Research Questions",
                        "Main Contributions",
                    ],
                    "needs": "Derived from Introduction RQs and Discussion",
                    "guidance": "Explicitly answer each research question. Summarize contributions. Do NOT introduce new material.",
                    "word_count_target": 500,
                },
                {
                    "name": "Recommendations",
                    "subsections": [
                        "Practical Recommendations (linked to findings)",
                    ],
                    "needs": "Grounded in study findings and limitations",
                    "guidance": "Each recommendation must cite a specific finding or limitation as its basis. Not opinions.",
                    "word_count_target": 300,
                },
                {
                    "name": "Future Research",
                    "subsections": [
                        "Unresolved Research Questions",
                        "Methodological Extensions",
                    ],
                    "needs": "Derived from Limitations and Discussion",
                    "guidance": "Name specific unresolved questions, not generic 'more research needed'.",
                    "word_count_target": 250,
                },
            ],
            "estimated_word_count": 6000,
            "key_themes": [],
            "research_questions": [],
        }

    num_sections = len(outline_data.get("sections", []))
    logger.info(
        "outline_plan_complete",
        extra={
            "section_count": num_sections,
            "parse_failed": parse_failed,
            "duration_s": round(time.perf_counter() - started_at, 2),
        },
    )

    return {
        "outline": outline_data,
        "current_step": "outline_plan",
        "steps_log": [
            f"✓ Research outline generated: {num_sections} sections planned"
        ],
    }
