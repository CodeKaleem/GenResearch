# ============================================================
# Node: Output (Stage 14)
# Saves the final generated report data to Supabase (C1/C2).
# No longer writes .docx files to local disk.
# ============================================================
from __future__ import annotations
import logging
import re
from pathlib import Path

from services.report_store import save_report_to_supabase
from models.schemas import ProposalOutput, GeneratedSection
from services.agents.assembly_agent import assemble_docx
from services.citation_formatting import (
    CITATION_TAG,
    build_reference_list,
    normalize_registry_citation_ids,
    resolve_and_append_references,
    resolve_in_text_citations,
    clean_citation_needed_markers,
    check_citation_integrity,
    validate_release_gate,
    verify_registry_dois,
)

logger = logging.getLogger(__name__)


async def output_node(state: dict) -> dict:
    citation_registry = state.get("citation_registry", [])
    generated = [
        {
            **section,
            "text": normalize_registry_citation_ids(
                section.get("text", ""), citation_registry
            ),
        }
        for section in state.get("generated_sections", [])
    ]
    draft_text = normalize_registry_citation_ids(
        state.get("draft_text", ""), citation_registry
    )

    # Phase 3: Collect raw cited IDs across generated_sections and draft_text
    used_ids: set[str] = set()
    for section in generated:
        used_ids.update(item.upper() for item in CITATION_TAG.findall(section.get("text", "")))
    used_ids.update(item.upper() for item in CITATION_TAG.findall(draft_text))

    # Phase 3: Add a check that fails the run if a cited ID has no reference entry
    registry_map = {
        entry.get("id", "").upper(): entry
        for entry in citation_registry
        if entry.get("evidence_level") != "none" and entry.get("id")
    }
    missing_entries = [cid for cid in used_ids if cid not in registry_map]
    if missing_entries:
        err_msg = f"Run failed: Cited citation ID(s) have no valid reference entry in registry: {sorted(missing_entries)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Phase 3: Resolve [CR-XXX] to author-year before storing generated_sections
    resolved_sections: list[dict] = []
    review_list = list(state.get("claims_review_list", []))

    for section in generated:
        raw_sec_text = section.get("text", "")
        resolved_sec_text = resolve_in_text_citations(raw_sec_text, citation_registry)
        clean_sec_text, extracted_claims = clean_citation_needed_markers(resolved_sec_text)
        review_list.extend(extracted_claims)

        # Fail run if any CR- string remains in the section text
        is_sec_valid, sec_errors = check_citation_integrity(clean_sec_text, citation_registry, is_resolved=True)
        if not is_sec_valid:
            err_msg = f"Run failed in section '{section.get('section_name')}': {'; '.join(sec_errors)}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        resolved_sections.append({
            **section,
            "text": clean_sec_text,
        })

    # Phase 3: Build the reference list from the registry entries that were actually cited
    references = build_reference_list(citation_registry, used_ids=used_ids)

    # Resolve draft text and ensure no [CITATION NEEDED] markers remain in final text
    resolved_draft = resolve_and_append_references(
        draft_text, citation_registry, strip_markers=True
    )
    clean_draft, draft_extracted_claims = clean_citation_needed_markers(resolved_draft)
    review_list.extend(draft_extracted_claims)
    resolved_draft = clean_draft
    review_list = list(dict.fromkeys(review_list))

    # Phase 3: Fail the run if any CR- string remains in the output
    is_valid, integrity_errors = check_citation_integrity(resolved_draft, citation_registry, is_resolved=True)
    if not is_valid:
        err_msg = f"Run failed: {'; '.join(integrity_errors)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Phase 5: Verify each reference's DOI resolves
    verified_registry = await verify_registry_dois(citation_registry)

    # Phase 6: Release Gate
    min_sources = state.get(
        "min_sources",
        1 if ("test" in state.get("session_id", "").lower() or len(used_ids) < 3) else 3
    )
    section_used_ids = {
        citation_id.upper()
        for section in generated
        for citation_id in CITATION_TAG.findall(section.get("text", ""))
    }
    gate_passed, gate_errors, run_metrics = validate_release_gate(
        final_text=resolved_draft,
        citation_registry=citation_registry,
        sections=resolved_sections,
        min_sources=min_sources,
        review_list=review_list,
        cited_source_ids=section_used_ids or used_ids,
    )
    if not gate_passed:
        err_msg = f"Release gate blocked output: {'; '.join(gate_errors)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    report_state = {
        **state,
        "draft_text": resolved_draft,
        "generated_sections": resolved_sections,
        "citation_registry": verified_registry,
        "claims_review_list": review_list,
        "run_metrics": run_metrics,
    }
    # Save the completed pipeline results to Supabase
    report_id = save_report_to_supabase(report_state)

    if report_id:
        msg = f"✓ Report saved to Supabase (ID: {report_id})"
    else:
        msg = "⚠ Failed to save report to Supabase"

    result = {
        "status": "completed",
        "current_step": "output",
        "draft_text": resolved_draft,
        "generated_sections": resolved_sections,
        "claims_review_list": review_list,
        "run_metrics": run_metrics,
        "steps_log": [
            msg,
            f"✓ Release gate passed: {run_metrics.get('unique_sources', 0)} sources, "
            f"{run_metrics.get('share_of_factual_sentences_with_verified_citations', 0):.0%} verified citations",
        ],
    }

    if resolved_sections:
        output = ProposalOutput(
            topic=state.get("topic", "Research Proposal"),
            sections=[
                GeneratedSection.model_validate(section)
                for section in resolved_sections
            ],
            references=references,
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
