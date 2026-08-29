# ============================================================
# Node: Output (Stage 14)
# Generates two .docx files: Draft + Completion Guide.
# ============================================================
from __future__ import annotations
import logging
from pathlib import Path

from services.docx_export import generate_draft_docx, generate_completion_guide_docx

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def output_node(state: dict) -> dict:
    session_id = state.get("session_id", "unknown")
    topic = state.get("topic", "Research Paper")
    draft_text = state.get("draft_text", "")
    citation_registry = state.get("citation_registry", [])
    citation_style = state.get("citation_style", "apa")
    sufficiency_report = state.get("sufficiency_report", {})
    flagged_items = state.get("flagged_items", [])
    cv_result = state.get("citation_verification_result", {})
    sc_result = state.get("section_critic_result", {})
    qa_result = state.get("final_qa_result", {})

    session_dir = OUTPUT_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Generate Draft .docx
    draft_path = session_dir / "draft.docx"
    generate_draft_docx(
        output_path=str(draft_path), draft_text=draft_text,
        citation_registry=citation_registry, citation_style=citation_style,
        title=topic,
    )

    # Generate Completion Guide .docx
    guide_path = session_dir / "completion_guide.docx"
    generate_completion_guide_docx(
        output_path=str(guide_path), topic=topic,
        sufficiency_report=sufficiency_report, flagged_items=flagged_items,
        citation_verification=cv_result, section_critique=sc_result,
        final_qa=qa_result,
    )

    return {
        "draft_file_path": str(draft_path),
        "completion_guide_file_path": str(guide_path),
        "status": "completed",
        "current_step": "output",
        "steps_log": [
            "✓ Draft and Completion Guide generated (.docx)"
        ],
    }
