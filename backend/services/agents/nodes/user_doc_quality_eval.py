# ============================================================
# Node: User-Document Quality Evaluation (Stage 2b — B2)
# Quality-checks user-uploaded documents before sufficiency eval.
# Model: nemotron-3-nano
#
# Runs after the questionnaire interrupt resumes.
# Rejects empty / cover-page-only / unextractable uploads.
# Rejected docs are flagged, NOT silently dropped.
# ============================================================
from __future__ import annotations

import json
import logging

from services.llm_service import call_llm
from services.agents.retry import increment_attempt

logger = logging.getLogger(__name__)

NODE_NAME = "user_doc_quality_eval"

USER_DOC_EVAL_SYSTEM = """You are GenResearch User-Document Quality Evaluator. You assess whether \
a user-uploaded document is substantive enough to chunk and use as source material.

A document PASSES if it:
1. Contains extractable, readable text (not just images or scans without OCR)
2. Has substantive content beyond a cover page / title page
3. Is actually relevant to the research topic (even loosely)

A document FAILS if it:
- Is empty or contains only metadata / headers
- Is a cover page with no body text
- Contains no extractable text at all

You MUST output valid JSON — nothing else.

Output format:
{
  "passed": true,
  "reasoning": "Brief explanation",
  "estimated_useful_length": 1500
}"""


async def _evaluate_single_doc(doc: dict, topic: str) -> dict:
    """Evaluate a single user-provided document."""
    content = doc.get("content", "") or doc.get("abstract_snippet", "")

    # Fast-path: if content is very short or empty, auto-fail
    if not content or len(content.strip()) < 50:
        return {
            "source_title": doc.get("title", "Unknown"),
            "passed": False,
            "reasoning": "Document has no usable content (empty or under 50 chars).",
            "estimated_useful_length": len(content.strip()) if content else 0,
        }

    prompt = f"""Evaluate whether this user-uploaded document is worth chunking for research.

Research Topic: "{topic}"

Document Title: {doc.get('title', 'Unknown')}
Content Preview (first 500 chars):
{content[:500]}

Total content length: {len(content)} characters

Evaluate this document:"""

    raw = await call_llm(
        prompt=prompt,
        agent_role="user_doc_quality_eval",
        system=USER_DOC_EVAL_SYSTEM,
        temperature=0.1,
        max_tokens=300,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Default to passing if we can't parse
        result = {
            "passed": True,
            "reasoning": "Evaluation parse failed — defaulting to pass.",
            "estimated_useful_length": len(content),
        }

    return {
        "source_title": doc.get("title", "Unknown"),
        **result,
    }


async def user_doc_quality_eval_node(state: dict) -> dict:
    """
    Stage 2b (B2): Evaluate user-uploaded documents for quality.
    Runs after questionnaire answers are submitted, before sufficiency eval.
    Rejected documents are flagged in flagged_items (not silently dropped).
    """
    topic = state["topic"]
    user_sources = state.get("user_provided_sources", [])
    attempt_update = increment_attempt(state, NODE_NAME)

    if not user_sources:
        return {
            "user_doc_quality_results": {},
            "current_step": NODE_NAME,
            **attempt_update,
            "steps_log": [
                "✓ No user documents to evaluate"
            ],
        }

    quality_results = {}
    new_flags = []
    passed_count = 0

    for doc in user_sources:
        result = await _evaluate_single_doc(doc, topic)
        title = result.get("source_title", "Unknown")
        quality_results[title] = result

        if result.get("passed", True):
            passed_count += 1
        else:
            new_flags.append({
                "node": NODE_NAME,
                "issue": f"Uploaded file '{title}' had no usable content and was skipped. "
                         f"Reason: {result.get('reasoning', 'Unknown')}",
                "attempts": 1,
                "action_required": "Upload a different version or provide additional material.",
            })

    # Filter user_provided_sources to keep only passed ones
    filtered_sources = [
        s for s in user_sources
        if quality_results.get(s.get("title", ""), {}).get("passed", True)
    ]

    return {
        "user_doc_quality_results": quality_results,
        "user_provided_sources": filtered_sources,
        "flagged_items": new_flags,
        "current_step": NODE_NAME,
        **attempt_update,
        "steps_log": [
            f"✓ User documents: {passed_count}/{len(user_sources)} passed quality check"
            + (f" ({len(new_flags)} rejected)" if new_flags else "")
        ],
    }
