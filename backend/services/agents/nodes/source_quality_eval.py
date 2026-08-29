# ============================================================
# Node: Source Quality Evaluation (Stage 7 — Branch B, Step 2)
# Per-source evaluation, internally parallel.
# Model: nemotron-3-nano (runs per-source — must stay cheap)
# ============================================================
from __future__ import annotations

import asyncio
import json
import logging

from services.llm_service import call_llm
from services.agents.retry import (
    increment_attempt,
)

logger = logging.getLogger(__name__)

NODE_NAME = "source_quality_eval"

SOURCE_EVAL_SYSTEM = """You are GenResearch Source Quality Evaluator. You assess a single academic \
source for credibility, recency, and relevance to the research topic.

Evaluate on these criteria:
1. **Credibility**: Is this from a peer-reviewed journal, conference, or reputable institution?
2. **Recency**: Is the publication date appropriate for the topic?
3. **Relevance**: Does it actually address the gap it was found for?

You MUST output valid JSON — nothing else.

Output format:
{
  "passed": true,
  "credibility": "high | medium | low",
  "recency_appropriate": true,
  "relevance_score": 8,
  "reasoning": "Brief explanation of the evaluation"
}"""


async def _evaluate_single_source(
    source: dict,
    topic: str,
    gap_topic: str,
) -> dict:
    """Evaluate a single source. Called concurrently for each source."""
    prompt = f"""Evaluate the following academic source for quality and relevance.

Research Topic: "{topic}"
Gap Being Addressed: "{gap_topic}"

Source:
- Title: {source.get('title', 'Unknown')}
- Authors: {source.get('authors', 'Unknown')}
- Year: {source.get('year', 'Unknown')}
- Source API: {source.get('source_api', 'Unknown')}
- Abstract: {source.get('abstract_snippet', 'Not available')}
- Citation Count: {source.get('citation_count', 'Unknown')}

Evaluate this source:"""

    raw = await call_llm(
        prompt=prompt,
        agent_role="source_quality_evaluator",
        system=SOURCE_EVAL_SYSTEM,
        temperature=0.1,
        max_tokens=500,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # If we can't parse, default to passing (don't block on parse failures)
        result = {
            "passed": True,
            "credibility": "medium",
            "recency_appropriate": True,
            "relevance_score": 5,
            "reasoning": "Evaluation parse failed — defaulting to pass.",
        }

    return {
        "source_title": source.get("title", "Unknown"),
        **result,
    }


async def source_quality_eval_node(state: dict) -> dict:
    """
    Branch B, Step 2 (Stage 7): Evaluate each source in parallel.
    Filters junk before it reaches the citation registry.

    Rate-limit aware: the per-model limiter in llm_service.py
    handles throttling automatically. We just fire all tasks.
    """
    topic = state["topic"]
    scraped = state.get("scraped_sources", [])

    attempt_update = increment_attempt(state, NODE_NAME)

    if not scraped:
        return {
            "source_quality_results": {},
            "current_step": "source_quality_eval",
            **attempt_update,
            "steps_log": [
                "✓ No scraped sources to evaluate"
            ],
        }

    # Evaluate all sources concurrently
    # The rate limiter in llm_service.py will throttle automatically
    tasks = [
        _evaluate_single_source(
            source=s,
            topic=topic,
            gap_topic=s.get("gap_topic", ""),
        )
        for s in scraped
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build results dict keyed by source title
    quality_results = {}
    passed_count = 0
    for i, result in enumerate(results):
        title = scraped[i].get("title", f"source_{i}")
        if isinstance(result, Exception):
            logger.warning("source_eval_failed", extra={"source": title, "error": str(result)})
            quality_results[title] = {
                "passed": True,  # Don't block on eval failures
                "reasoning": f"Evaluation error: {result}",
            }
            passed_count += 1
        else:
            quality_results[title] = result
            if result.get("passed", True):
                passed_count += 1

    return {
        "source_quality_results": quality_results,
        "current_step": "source_quality_eval",
        **attempt_update,
        "steps_log": [
            f"✓ Source quality: {passed_count}/{len(scraped)} sources passed evaluation"
        ],
    }
