# ============================================================
# GenResearch — Report Store (C2)
# Saves generated reports to Supabase instead of local files.
# ============================================================
import json
import logging
from database.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def build_completion_guide_text(state: dict) -> str:
    """Builds a markdown string for the completion guide based on state."""
    topic = state.get("topic", "Research Paper")
    sufficiency = state.get("sufficiency_report", {})
    flags = state.get("flagged_items", [])
    cv_res = state.get("citation_verification_result", {})
    sc_res = state.get("section_critic_result", {})
    qa_res = state.get("final_qa_result", {})

    lines = [
        f"# Completion Guide: {topic}",
        "",
        "## 1. Sufficiency Analysis",
        f"Overall Assessment: {sufficiency.get('overall_assessment', 'Unknown')}",
        "",
        "### Section Breakdown:"
    ]

    for section, data in sufficiency.get("sections", {}).items():
        lines.append(f"- **{section}** ({data.get('confidence')}): {data.get('reasoning')}")

    lines.append("")
    lines.append("## 2. Action Items (Flags)")
    if not flags:
        lines.append("No flagged items! The pipeline ran smoothly.")
    else:
        for idx, flag in enumerate(flags, 1):
            lines.append(f"### Issue {idx} (from {flag.get('node')})")
            lines.append(f"**Problem:** {flag.get('issue')}")
            lines.append(f"**Action Required:** {flag.get('action_required')}")

    lines.append("")
    lines.append("## 3. Quality Metrics")
    lines.append(f"- **Citation Grounding:** {cv_res.get('coverage_score', 0):.0%} coverage")
    lines.append(f"- **Writing Quality:** {sc_res.get('overall_score', 0)}/10")
    lines.append(f"- **Overall Pipeline QA:** {qa_res.get('overall_score', 0)}/10")
    lines.append("")
    lines.append(f"**Final Summary:** {qa_res.get('summary', '')}")

    return "\n".join(lines)


def save_report_to_supabase(state: dict) -> str:
    """
    Save the completed pipeline results to Supabase `research_reports`.
    Returns the ID of the inserted record.
    """
    sb = get_supabase()

    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "")
    topic = state.get("topic", "Unknown")
    draft_text = state.get("draft_text", "")
    outline = state.get("outline", {})
    citation_registry = state.get("citation_registry", [])

    completion_guide = build_completion_guide_text(state)

    data = {
        "session_id": session_id,
        "user_id": user_id,
        "topic": topic,
        "draft_text": draft_text,
        "completion_guide": completion_guide,
        "outline": outline,
        "citation_registry": citation_registry,
    }

    try:
        # Using upsert on session_id to avoid duplicates if run multiple times
        res = sb.table("research_reports").upsert(
            data, on_conflict="session_id"
        ).execute()
        return res.data[0]["id"] if res.data else ""
    except Exception as e:
        logger.error(f"Failed to save report to Supabase: {e}")
        return ""
