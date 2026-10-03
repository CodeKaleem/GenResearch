# ============================================================
# Node: Output (Stage 14)
# Saves the final generated report data to Supabase (C1/C2).
# No longer writes .docx files to local disk.
# ============================================================
from __future__ import annotations
import logging
from pathlib import Path

from services.report_store import save_report_to_supabase
from models.schemas import ProposalOutput, GeneratedSection
from services.agents.assembly_agent import assemble_docx
from services.citation_formatting import (
    CITATION_TAG,
    build_reference_list,
    resolve_and_append_references,
    resolve_in_text_citations,
)

logger = logging.getLogger(__name__)


async def output_node(state: dict) -> dict:
    citation_registry = state.get("citation_registry", [])
    resolved_draft = resolve_and_append_references(
        state.get("draft_text", ""), citation_registry
    )
    report_state = {**state, "draft_text": resolved_draft}
    # Save the entire completed pipeline results to Supabase
    report_id = save_report_to_supabase(report_state)

    if report_id:
        msg = f"✓ Report saved to Supabase (ID: {report_id})"
    else:
        msg = "⚠ Failed to save report to Supabase"

    result = {
        "status": "completed",
        "current_step": "output",
        "steps_log": [msg],
    }
    generated = state.get("generated_sections", [])
    if generated:
        used_ids = set(CITATION_TAG.findall("\n".join(
            section.get("text", "") for section in generated
        )))
        output = ProposalOutput(
            topic=state.get("topic", "Research Proposal"),
            sections=[
                GeneratedSection.model_validate({
                    **section,
                    "text": resolve_in_text_citations(section.get("text", ""), citation_registry),
                })
                for section in generated
            ],
            references=build_reference_list(citation_registry, used_ids=used_ids),
            session_id=state.get("session_id"),
        )
        output_path = Path("storage") / "outputs" / f"{state.get('session_id', 'proposal')}.docx"
        try:
            result["draft_file_path"] = assemble_docx(output, output_path)
            result["steps_log"].append("✓ Verified proposal exported as DOCX")
        except Exception as error:
            logger.warning("proposal_docx_export_failed", extra={"error": str(error)})
            result["steps_log"].append("⚠ DOCX export failed; Supabase report remains available")
    return result
