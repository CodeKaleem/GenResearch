# ============================================================
# Node: Output (Stage 14)
# Saves the final generated report data to Supabase (C1/C2).
# No longer writes .docx files to local disk.
# ============================================================
from __future__ import annotations
import logging

from services.report_store import save_report_to_supabase

logger = logging.getLogger(__name__)


async def output_node(state: dict) -> dict:
    # Save the entire completed pipeline results to Supabase
    report_id = save_report_to_supabase(state)

    if report_id:
        msg = f"✓ Report saved to Supabase (ID: {report_id})"
    else:
        msg = "⚠ Failed to save report to Supabase"

    return {
        "status": "completed",
        "current_step": "output",
        "steps_log": [msg],
    }
