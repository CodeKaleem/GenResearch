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

logger = logging.getLogger(__name__)


async def output_node(state: dict) -> dict:
    # Save the entire completed pipeline results to Supabase
    report_id = save_report_to_supabase(state)

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
        output = ProposalOutput(
            topic=state.get("topic", "Research Proposal"),
            sections=[GeneratedSection.model_validate(section) for section in generated],
            references=[entry.get("title", "") for entry in state.get("citation_registry", [])],
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
