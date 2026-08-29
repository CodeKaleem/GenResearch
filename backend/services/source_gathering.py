# ============================================================
# Service: Source Gathering
# Gap-driven academic source retrieval.
#
# Priority order (spec §3.1):
#   1. Semantic Scholar API (structured, clean metadata)
#   2. arXiv API (preprints, open access)
#   3. CrossRef API (DOI resolution)
#   4. OpenAlex API (comprehensive coverage)
#   5. Web search fallback (Tavily + trafilatura) — only if academic sparse
#
# Design rule: gap-driven retrieval, NOT quota-driven.
#   "find a source addressing X counter-argument" — correct.
#   "find 5 sources" — WRONG.
# ============================================================
from __future__ import annotations

import logging
import asyncio
from datetime import datetime
from typing import Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# Timeout for external API calls
API_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def search_semantic_scholar(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> list[dict]:
    """
    Search Semantic Scholar for academic papers.
    Returns structured source metadata.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,url,abstract,citationCount,externalIds",
    }
    headers = {}
    if settings.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=API_TIMEOUT)

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("semantic_scholar_error", extra={"status": resp.status})
                return []
            data = await resp.json()

        papers = data.get("data", [])
        results = []
        for p in papers:
            authors = ", ".join(
                a.get("name", "") for a in (p.get("authors") or [])
            )
            doi = (p.get("externalIds") or {}).get("DOI", "")
            results.append({
                "title": p.get("title", "Unknown"),
                "authors": authors,
                "year": p.get("year"),
                "url": p.get("url", ""),
                "doi": doi,
                "abstract_snippet": (p.get("abstract") or "")[:300],
                "citation_count": p.get("citationCount", 0),
                "source_api": "semantic_scholar",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return results

    except Exception as e:
        logger.warning("semantic_scholar_exception", extra={"error": str(e)})
        return []
    finally:
        if own_session:
            await session.close()


async def search_arxiv(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> list[dict]:
    """
    Search arXiv for preprints via their Atom API.
    """
    import xml.etree.ElementTree as ET

    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
    }

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=API_TIMEOUT)

    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.warning("arxiv_error", extra={"status": resp.status})
                return []
            text = await resp.text()

        # Parse Atom XML
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(text)
        results = []

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)

            authors = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None
            ]

            # Get the abs link
            link = ""
            for l in entry.findall("atom:link", ns):
                if l.get("type") == "text/html":
                    link = l.get("href", "")
                    break

            year = None
            if published_el is not None and published_el.text:
                year = int(published_el.text[:4])

            results.append({
                "title": (title_el.text or "").strip().replace("\n", " ") if title_el is not None else "Unknown",
                "authors": ", ".join(authors),
                "year": year,
                "url": link,
                "doi": "",
                "abstract_snippet": ((summary_el.text or "").strip()[:300]) if summary_el is not None else "",
                "source_api": "arxiv",
                "accessed_date": datetime.utcnow().isoformat(),
            })

        return results

    except Exception as e:
        logger.warning("arxiv_exception", extra={"error": str(e)})
        return []
    finally:
        if own_session:
            await session.close()


async def search_openalex(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> list[dict]:
    """
    Search OpenAlex for academic works.
    Free, no API key required.
    """
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": limit,
        "select": "title,authorships,publication_year,doi,id,cited_by_count",
    }
    headers = {"User-Agent": "GenResearch/0.2.0 (mailto:research@genresearch.dev)"}

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=API_TIMEOUT)

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("openalex_error", extra={"status": resp.status})
                return []
            data = await resp.json()

        results = []
        for work in data.get("results", []):
            authors = ", ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (work.get("authorships") or [])[:5]
            )
            doi = work.get("doi", "") or ""
            # OpenAlex DOIs are full URLs; extract just the DOI
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]

            results.append({
                "title": work.get("title", "Unknown") or "Unknown",
                "authors": authors,
                "year": work.get("publication_year"),
                "url": work.get("id", ""),
                "doi": doi,
                "abstract_snippet": "",  # OpenAlex doesn't always include abstracts in search
                "citation_count": work.get("cited_by_count", 0),
                "source_api": "openalex",
                "accessed_date": datetime.utcnow().isoformat(),
            })

        return results

    except Exception as e:
        logger.warning("openalex_exception", extra={"error": str(e)})
        return []
    finally:
        if own_session:
            await session.close()


async def gather_sources_for_gaps(
    gaps: list[dict],
    existing_sources: list[dict] | None = None,
    sources_per_gap: int = 3,
) -> tuple[list[dict], list[dict]]:
    """
    Gap-driven source gathering.

    Args:
        gaps:            List of gap dicts from the gap report, each with a 'search_query'.
        existing_sources: Sources already available (to avoid duplicates).
        sources_per_gap: Max sources to find per gap.

    Returns:
        (found_sources, unfilled_gaps) — sources found + gaps with no results.
    """
    existing_titles = set()
    if existing_sources:
        existing_titles = {s.get("title", "").lower() for s in existing_sources}

    all_found: list[dict] = []
    unfilled: list[dict] = []

    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        for gap in gaps:
            query = gap.get("search_query") or gap.get("topic", "")
            if not query:
                unfilled.append(gap)
                continue

            gap_sources: list[dict] = []

            # Priority 1: Semantic Scholar
            ss_results = await search_semantic_scholar(query, limit=sources_per_gap, session=session)
            for s in ss_results:
                if s["title"].lower() not in existing_titles:
                    s["gap_topic"] = gap.get("topic", "")
                    gap_sources.append(s)
                    existing_titles.add(s["title"].lower())

            # Priority 2: arXiv (if Semantic Scholar didn't fill the gap)
            if len(gap_sources) < sources_per_gap:
                remaining = sources_per_gap - len(gap_sources)
                arxiv_results = await search_arxiv(query, limit=remaining, session=session)
                for s in arxiv_results:
                    if s["title"].lower() not in existing_titles:
                        s["gap_topic"] = gap.get("topic", "")
                        gap_sources.append(s)
                        existing_titles.add(s["title"].lower())

            # Priority 3: OpenAlex (if still not enough)
            if len(gap_sources) < sources_per_gap:
                remaining = sources_per_gap - len(gap_sources)
                oa_results = await search_openalex(query, limit=remaining, session=session)
                for s in oa_results:
                    if s["title"].lower() not in existing_titles:
                        s["gap_topic"] = gap.get("topic", "")
                        gap_sources.append(s)
                        existing_titles.add(s["title"].lower())

            if gap_sources:
                all_found.extend(gap_sources)
            else:
                unfilled.append(gap)

            # Small delay between gaps to be respectful to APIs
            await asyncio.sleep(0.5)

    logger.info(
        "source_gathering_complete",
        extra={
            "gaps_searched": len(gaps),
            "sources_found": len(all_found),
            "unfilled_gaps": len(unfilled),
        },
    )

    return all_found, unfilled
