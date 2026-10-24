# ============================================================
# Node: Source Quality Evaluation (Stage 7 — Branch B, Step 2)
# Pre-filters with deterministic rules; batches remaining sources.
# Model: light (cheap — short JSON outputs only)
# ============================================================
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Optional

from services.llm_service import call_llm
from services.agents.json_utils import parse_llm_json
from services.agents.retry import increment_attempt

logger = logging.getLogger(__name__)

NODE_NAME = "source_quality_eval"

# How many sources to evaluate in a single LLM call
BATCH_SIZE = 8
# Minimum abstract length to pass the pre-filter without LLM
MIN_ABSTRACT_LEN = 50
# Papers older than this are pre-filtered out (unless no others available)
MIN_YEAR = 1990

SOURCE_EVAL_SYSTEM = """You are GenResearch Source Quality Evaluator. \
You assess a batch of academic sources for credibility, recency, and relevance.

You MUST output ONLY valid JSON — no prose, no markdown fences.

Output format (an object keyed by the index string "0", "1", ... matching input order):
{
  "0": {"passed": true, "credibility": "high|medium|low", "relevance_score": 8, "reasoning": "one line"},
  "1": {"passed": false, "credibility": "low", "relevance_score": 2, "reasoning": "one line"}
}"""


def _keyword_overlap(text: str, topic: str) -> int:
    """Count how many topic words (≥4 chars) appear in text."""
    words = {w.lower() for w in re.findall(r"\w{4,}", topic)}
    haystack = text.lower()
    return sum(1 for w in words if w in haystack)


def _pre_filter_source(source: dict, topic: str) -> tuple[bool, str]:
    """
    Deterministic pre-filter. Returns (passed, reason).
    Sources that clearly pass or fail do not need an LLM call.
    """
    title = source.get("title", "") or ""
    abstract = source.get("abstract_snippet", "") or ""
    year = source.get("year")
    combined = f"{title} {abstract}"

    if len(abstract) < MIN_ABSTRACT_LEN:
        return False, "No usable abstract"

    # Reject very old papers unless they're classic works (high citation count)
    try:
        y = int(year)
    except (TypeError, ValueError):
        return False, "Missing or invalid publication year"
    try:
        cites = int(source.get("citation_count", 0) or 0)
    except (TypeError, ValueError):
        cites = 0
    if y < MIN_YEAR and cites < 100:
        return False, f"Too old ({y}) and low citations"

    # Require at least 1 keyword from the topic
    if _keyword_overlap(combined, topic) == 0:
        return False, "No topic keywords found in title/abstract"

    # Indeterminate — needs LLM
    return True, "pre-filter-pass"


async def _evaluate_batch(
    sources: list[dict],
    indices: list[int],
    topic: str,
    gap_topic: str,
) -> dict[int, dict]:
    """Evaluate a batch of sources in a single LLM call."""
    source_payload = {}
    for local_idx, source in enumerate(sources):
        source_payload[str(local_idx)] = {
            "title": source.get("title", "Unknown"),
            "year": source.get("year", "Unknown"),
            "abstract": (source.get("abstract_snippet", "") or "")[:300],
            "citations": source.get("citation_count", 0),
        }

    prompt = (
        f'Research topic: "{topic}"\n'
        f'Gap addressed: "{gap_topic}"\n\n'
        f"Sources to evaluate:\n{json.dumps(source_payload, ensure_ascii=True)}\n\n"
        "Evaluate each source. Output JSON only."
    )

    raw = await call_llm(
        prompt=prompt,
        agent_role="source_quality_evaluator",
        system=SOURCE_EVAL_SYSTEM,
        temperature=0.0,
        max_tokens=300,
    )

    parsed = parse_llm_json(raw)
    results: dict[int, dict] = {}
    for local_idx, global_idx in enumerate(indices):
        key = str(local_idx)
        entry = (parsed or {}).get(key)
        if not isinstance(entry, dict):
            # Parse fallback: default to pass
            entry = {
                "passed": True,
                "credibility": "medium",
                "relevance_score": 5,
                "reasoning": "Batch eval parse failed — defaulting to pass.",
            }
        results[global_idx] = entry
    return results


async def source_quality_eval_node(state: dict) -> dict:
    """
    Branch B, Step 2 (Stage 7): Pre-filter + batch-evaluate sources.

    Algorithm:
    1. Deterministic pre-filter (no LLM): reject sources with no abstract,
       no keyword overlap, or that are too old.
    2. Batch remaining sources (BATCH_SIZE per call) into concurrent LLM evals.
    3. Merge results; failed sources are removed from scraped_sources.
    """
    started_at = time.perf_counter()
    topic = state.get("topic", "")
    scraped = state.get("scraped_sources", [])

    logger.info("source_quality_eval_started", extra={"source_count": len(scraped)})
    attempt_update = increment_attempt(state, NODE_NAME)

    if not scraped:
        logger.info(
            "source_quality_eval_complete",
            extra={
                "source_count": 0,
                "llm_request_count": 0,
                "duration_s": round(time.perf_counter() - started_at, 2),
            },
        )
        return {
            "source_quality_results": {},
            "current_step": "source_quality_eval",
            **attempt_update,
            "steps_log": ["✓ No scraped sources to evaluate"],
        }

    # ── Step 1: deterministic pre-filter ──────────────────────────────────
    pre_passed: list[int] = []   # global indices that passed pre-filter
    pre_failed: list[int] = []   # global indices rejected deterministically
    pre_results: dict[str, dict] = {}

    for i, source in enumerate(scraped):
        passed, reason = _pre_filter_source(source, topic)
        if not passed:
            pre_failed.append(i)
            pre_results[source.get("title", f"source_{i}")] = {
                "passed": False,
                "credibility": "low",
                "relevance_score": 0,
                "reasoning": f"Pre-filter: {reason}",
            }
        else:
            pre_passed.append(i)

    logger.info(
        "source_quality_pre_filter",
        extra={
            "total": len(scraped),
            "pre_passed": len(pre_passed),
            "pre_failed": len(pre_failed),
        },
    )

    # ── Step 2: batch LLM evaluation of remaining sources ─────────────────
    quality_results: dict[str, dict] = dict(pre_results)

    if pre_passed:
        # Split into batches and evaluate concurrently
        batches: list[tuple[list[dict], list[int], str]] = []
        for batch_start in range(0, len(pre_passed), BATCH_SIZE):
            batch_indices = pre_passed[batch_start: batch_start + BATCH_SIZE]
            batch_sources = [scraped[i] for i in batch_indices]
            gap_topic = batch_sources[0].get("gap_topic", "")
            batches.append((batch_sources, batch_indices, gap_topic))

        tasks = [
            _evaluate_batch(batch_sources, batch_indices, topic, gap_topic)
            for batch_sources, batch_indices, gap_topic in batches
        ]
        batch_results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for batch_result in batch_results_list:
            if isinstance(batch_result, Exception):
                logger.warning("source_quality_batch_failed", extra={"error": str(batch_result)})
                continue
            for global_idx, result in batch_result.items():
                title = scraped[global_idx].get("title", f"source_{global_idx}")
                quality_results[title] = result

    # Fill any missing entries (safety net)
    for i, source in enumerate(scraped):
        title = source.get("title", f"source_{i}")
        if title not in quality_results:
            quality_results[title] = {
                "passed": True,
                "credibility": "medium",
                "relevance_score": 5,
                "reasoning": "Evaluation missing — defaulting to pass.",
            }

    passed_count = sum(1 for r in quality_results.values() if r.get("passed", True))
    llm_calls = len(batches) if pre_passed else 0
    logger.info(
        "source_quality_eval_complete",
        extra={
            "source_count": len(scraped),
            "pre_filtered_count": len(pre_failed),
            "llm_request_count": llm_calls,
            "passed_count": passed_count,
            "duration_s": round(time.perf_counter() - started_at, 2),
        },
    )

    return {
        "source_quality_results": quality_results,
        "current_step": "source_quality_eval",
        **attempt_update,
        "steps_log": [
            f"✓ Source quality: {passed_count}/{len(scraped)} passed "
            f"(pre-filtered {len(pre_failed)}, {llm_calls} LLM batch call(s))"
        ],
    }
