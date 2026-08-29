# ============================================================
# GenResearch — Pipeline State Schema
# Single shared state object for the entire multi-agent graph.
#
# Design rule (spec §2.4, non-negotiable):
#   The LLM is a stateless, disposable reasoning function.
#   ALL accumulated context lives here, never inside a model's
#   own memory. Any node must be swappable to a different model
#   without losing context.
#
# Design rule (spec §5.3):
#   Parallel branches write to SEPARATE, non-overlapping state
#   keys. The join node merges them explicitly.
#
# IMPORTANT — LangGraph concurrency:
#   Any key that can be written by two parallel branches must
#   use Annotated[..., reducer] so LangGraph knows how to merge
#   concurrent updates. Without this, you get:
#   INVALID_CONCURRENT_GRAPH_UPDATE
# ============================================================
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


# ── Custom Reducers ──────────────────────────────────────────

def _merge_dicts(left: dict, right: dict) -> dict:
    """Merge two dicts, with right overriding left on key conflict."""
    merged = dict(left) if left else {}
    if right:
        merged.update(right)
    return merged


def _last_value(left: str, right: str) -> str:
    """Last-write-wins for scalar string fields."""
    return right if right else left


class ProposalState(TypedDict, total=False):
    """
    Every node reads from and writes to this single shared object.
    Fields are grouped by the pipeline stage that produces them.

    `total=False` because not every field exists at every stage —
    early nodes only populate early fields. Downstream nodes must
    handle missing keys gracefully.

    Keys touched by parallel branches use Annotated reducers:
      - steps_log:    list concat  (operator.add)
      - flagged_items: list concat (operator.add)
      - retry_counts:  dict merge  (_merge_dicts)
      - retry_feedback: dict merge (_merge_dicts)
      - current_step:  last-write  (_last_value)
      - status:        last-write  (_last_value)
    """

    # ── Stage 1: Topic Input ─────────────────────────────────
    topic: str
    user_id: str
    session_id: str            # unique per pipeline run
    citation_style: str        # "apa" | "ieee" | "mla" | "chicago"

    # ── Stage 2: Questionnaire Agent ─────────────────────────
    questionnaire_questions: list[dict]     # generated questions
    questionnaire_answers: dict             # user's responses

    # ── Stage 2b: User-Document Quality Eval (B2) ────────────
    user_doc_quality_results: dict          # { filename: { passed, reasoning } }

    # ── Stage 3: Sufficiency Evaluator ───────────────────────
    # Per-section confidence: { section_name: "well_supported"|"adequate"|"weak" }
    sufficiency_report: dict

    # ── Stage 3b: Scrape Permission (B3) ─────────────────────
    scrape_permission_granted: bool         # user's decision

    # ── Stage 4: Gap Report ──────────────────────────────────
    # { covered: [...], missing: [{ topic, reason }, ...] }
    gap_report: dict

    # ── Stage 5 (Branch A): Outline / Research Plan ──────────
    # { sections: [{ name, needs, ... }, ...] }
    # Written by Branch A only — Branch B does NOT touch this key.
    outline: dict

    # ── Stage 6 (Branch B): Source Gathering ──────────────────
    user_provided_sources: list[dict]
    scraped_sources: list[dict]

    # ── Stage 7 (Branch B): Source Quality Evaluation ────────
    # { source_id: { passed: bool, reasoning: str }, ... }
    source_quality_results: dict

    # ── Stage 8 (Branch B): Ingestion + Citation Registry ────
    # The citation registry is the SINGLE SOURCE OF TRUTH for citations.
    # No agent may ever generate a citation string that isn't here.
    # [{ id, title, authors, url, accessed_date, tag: "user"|"scraped",
    #    year, doi, source_type, abstract_snippet }]
    citation_registry: list[dict]

    # ── Stage 10: Draft Agent ────────────────────────────────
    draft_text: str

    # ── Stage 11 (Branch C): Citation/Claim Verification ─────
    # { verified_count, unverified_claims: [...], score, details }
    citation_verification_result: dict

    # ── Stage 12 (Branch D): Section Critic ──────────────────
    # { sections: { name: { score, feedback, issues } }, overall_score }
    section_critic_result: dict

    # ── Stage 13: Final QA ───────────────────────────────────
    # { passed, score, issues: [...], summary }
    final_qa_result: dict

    # ── Retry & Flagging (spec §6) ───────────────────────────
    # These MUST be Annotated because parallel branches can both
    # increment retry counts or flag items simultaneously.
    retry_counts: Annotated[dict, _merge_dicts]
    retry_feedback: Annotated[dict, _merge_dicts]
    flagged_items: Annotated[list[dict], operator.add]

    # ── Pipeline Metadata ────────────────────────────────────
    # These MUST be Annotated because parallel branches both
    # write current_step and steps_log simultaneously.
    status: Annotated[str, _last_value]
    current_step: Annotated[str, _last_value]
    steps_log: Annotated[list[str], operator.add]

    # ── User approval feedback (B4) ──────────────────────────
    approval_comment: str              # user's comment/edit on the outline
