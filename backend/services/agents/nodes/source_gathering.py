# ============================================================
# Node: Source Gathering (Stage 6 — Branch B, Step 1)
# Gap-driven and scholarly retrieval — all APIs run concurrently.
# Generates 4-6 targeted queries from research questions,
# not from section names.
# Writes to: state.scraped_sources
# ============================================================
from __future__ import annotations

import logging
import time

from config import settings
from services.source_gathering import gather_sources_for_gaps

logger = logging.getLogger(__name__)

MIN_SOURCE_TARGET = 5
# Hard cap on queries to prevent redundant searches.
MAX_QUERIES = 6


def _build_smart_queries(topic: str, outline: dict, gap_report: dict) -> list[dict]:
    """
    Build up to 6 targeted search queries from research questions and gaps.

    Rules:
    - Use research_questions from outline if available (most targeted).
    - Add the bare topic as a fallback query.
    - Keep the topic query and up to 1 theme-based query.
    - NEVER add section names (Abstract, Introduction, …) as queries.
    - Reserve one query for case studies when enabled.
    """
    seen: set[str] = set()
    gaps: list[dict] = []

    def add(query: str, label: str, source_category: str | None = None) -> dict | None:
        q = query.strip()
        if not q:
            return None
        if q.lower() in seen:
            existing = next(gap for gap in gaps if gap["search_query"].lower() == q.lower())
            if source_category:
                existing["source_category"] = source_category
            return existing
        seen.add(q.lower())
        gap = {"topic": label, "search_query": q}
        if source_category:
            gap["source_category"] = source_category
        gaps.append(gap)
        return gap

    # 1. Research questions from outline (best signal)
    rqs = outline.get("research_questions", [])
    for rq in rqs[:3]:
        q = str(rq).strip(" ?").strip()
        if q:
            add(f"{topic} {q}", q[:60])

    # 2. Gap topics from the gap report (targeted gaps)
    for gap in (gap_report.get("missing", []) or [])[:1]:
        q = gap.get("search_query") or gap.get("topic", "")
        if q:
            add(q, gap.get("topic", q[:60]))

    # 3. Bare topic — always include as anchor query
    add(topic, topic)

    # 4. Key theme as a secondary query
    for theme in (outline.get("key_themes", []) or [])[:1]:
        t = str(theme).strip()
        if t:
            add(f"{topic} {t}", t[:60])

    case_study_gap = None
    if settings.SCRAPER_ENABLE_CASE_STUDIES:
        case_study_gap = add(
            f"{topic} case study",
            "Case study examples",
            source_category="case_study_candidate",
        )

    regular_gaps = [gap for gap in gaps if gap is not case_study_gap]
    if case_study_gap:
        return [*regular_gaps[:MAX_QUERIES - 1], case_study_gap]
    return gaps[:MAX_QUERIES]


async def source_gathering_node(state: dict) -> dict:
    """
    Branch B, Step 1 (Stage 6): Fetch academic sources via scholarly search APIs.

    Improvements over previous version:
    - Generates up to 6 targeted queries from research questions, gaps, and case studies,
      not from section names (was producing 22 near-duplicate queries).
    - All APIs (SS, Crossref, OpenAlex, arXiv) run concurrently per query.
    - All queries run concurrently (bounded concurrency in gather_sources_for_gaps).
    - Removes the Playwright scraping pass (was timing out on bot challenges).
    - Tracks wall time and logs per-stage timing for future diagnosis.
    """
    t0 = time.perf_counter()

    topic = state.get("topic", "")
    outline = state.get("outline", {})
    gap_report = state.get("gap_report", {})
    existing = list(state.get("user_provided_sources", []))
    min_target = state.get("min_sources", MIN_SOURCE_TARGET)

    # Build smart queries
    gaps = _build_smart_queries(topic, outline, gap_report)

    logger.info(
        "source_gathering_queries",
        extra={
            "query_count": len(gaps),
            "request_count": len(gaps) * 4,
            "queries": [g["search_query"] for g in gaps],
        },
    )

    usable_existing = [s for s in existing if (s.get("content") or s.get("abstract_snippet"))]
    sources_per_gap = max(2, min_target)

    found_sources, unfilled_gaps, errors = await gather_sources_for_gaps(
        gaps=gaps,
        existing_sources=existing,
        sources_per_gap=sources_per_gap,
    )

    elapsed = time.perf_counter() - t0

    # Flag unfilled gaps
    new_flags = []
    for gap in unfilled_gaps:
        new_flags.append({
            "node": "source_gathering",
            "issue": (
                f"Could not find sources for: {gap.get('topic', 'Unknown')}. "
                f"Reason: {gap.get('reason', 'No results from academic APIs.')}"
            ),
            "attempts": 1,
            "action_required": "You may need to find sources for this topic manually.",
        })

    steps_log = [
        f"✓ Gathered {len(found_sources)} academic sources in {elapsed:.1f}s "
        f"({len(gaps)} queries, target: {min_target})"
        + (f" ({len(unfilled_gaps)} queries unfilled)" if unfilled_gaps else "")
    ]
    if errors:
        steps_log.append(f"⚠ Source API notices: {len(errors)}")

    return {
        "scraped_sources": found_sources,
        "flagged_items": new_flags,
        "current_step": "source_gathering",
        "steps_log": steps_log,
    }
