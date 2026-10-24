# ============================================================
# Service: Source Gathering
# Gap-driven academic source retrieval via REST APIs only.
#
# Priority order:
#   1. Semantic Scholar API  (structured, clean metadata)
#   2. CrossRef API          (DOI resolution, reliable)
#   3. OpenAlex API          (no key needed, comprehensive)
#   4. arXiv API             (preprints, CS-heavy)
#
# All 4 APIs run CONCURRENTLY per gap.
# All gaps run CONCURRENTLY (bounded by _GAP_CONCURRENCY).
#
# No Playwright / browser scraping — replaced by direct REST calls.
# ============================================================
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# Timeout for external API calls
API_TIMEOUT = aiohttp.ClientTimeout(total=20)
ABSTRACT_SNIPPET_LENGTH = 1500

# Max simultaneous gap queries to avoid hammering APIs
_GAP_CONCURRENCY = 4


class _AbstractTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_abstract(abstract: str) -> str:
    parser = _AbstractTextParser()
    parser.feed(abstract or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _crossref_year(item: dict) -> int | None:
    for field in ("published-print", "issued", "published-online"):
        date_parts = (item.get(field) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            try:
                return int(date_parts[0][0])
            except (TypeError, ValueError):
                continue
    return None


def _title_key(title: object) -> str:
    return str(title or "").strip().casefold()


# ──────────────────────────────────────────────────────────
# Individual API search functions
# ──────────────────────────────────────────────────────────

async def search_semantic_scholar(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """Search Semantic Scholar REST API. Returns structured source metadata."""
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
            if resp.status == 429:
                logger.warning("semantic_scholar_rate_limited")
                return {"status": "rate_limited", "results": []}
            if resp.status != 200:
                logger.warning("semantic_scholar_error", extra={"status": resp.status})
                return {"status": "error", "error": f"HTTP {resp.status}", "results": []}
            data = await resp.json()

        papers = data.get("data", [])
        results = []
        for p in papers:
            authors = ", ".join(a.get("name", "") for a in (p.get("authors") or []))
            doi = (p.get("externalIds") or {}).get("DOI", "")
            results.append({
                "title": p.get("title", "Unknown"),
                "authors": authors,
                "year": p.get("year"),
                "url": p.get("url", ""),
                "doi": doi,
                "abstract_snippet": (p.get("abstract") or "")[:ABSTRACT_SNIPPET_LENGTH],
                "citation_count": p.get("citationCount", 0),
                "source_api": "semantic_scholar",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return {"status": "success", "results": results}

    except asyncio.TimeoutError:
        logger.warning("semantic_scholar_timeout")
        return {"status": "timeout", "results": []}
    except Exception as e:
        logger.warning("semantic_scholar_exception", extra={"error": str(e)})
        return {"status": "error", "error": str(e), "results": []}
    finally:
        if own_session:
            await session.close()


async def search_crossref(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """Search CrossRef REST API for DOIs and scholarly works."""
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": limit,
        "select": "title,author,published-print,published-online,issued,DOI,URL,abstract,is-referenced-by-count",
    }
    headers = {"User-Agent": "GenResearch/0.2.0 (mailto:research@genresearch.dev)"}

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=API_TIMEOUT)

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("crossref_error", extra={"status": resp.status})
                return {"status": "error", "error": f"HTTP {resp.status}", "results": []}
            data = await resp.json()

        results = []
        for item in data.get("message", {}).get("items", []):
            titles = item.get("title") or []
            title = (titles[0] if titles else None) or "Unknown"
            author_names = []
            for a in item.get("author", []):
                if "given" in a and "family" in a:
                    author_names.append(f"{a['given']} {a['family']}")
                elif "family" in a:
                    author_names.append(a["family"])
                elif "name" in a:
                    author_names.append(a["name"])
            authors = ", ".join(author_names) if author_names else "Unknown"
            abstract = _clean_abstract(item.get("abstract") or "")
            results.append({
                "title": title,
                "authors": authors,
                "year": _crossref_year(item),
                "url": item.get("URL", ""),
                "doi": item.get("DOI", ""),
                "abstract_snippet": abstract[:ABSTRACT_SNIPPET_LENGTH],
                "citation_count": item.get("is-referenced-by-count", 0),
                "source_api": "crossref",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return {"status": "success", "results": results}

    except asyncio.TimeoutError:
        logger.warning("crossref_timeout")
        return {"status": "timeout", "results": []}
    except Exception as e:
        logger.warning("crossref_exception", extra={"error": str(e)})
        return {"status": "error", "error": str(e), "results": []}
    finally:
        if own_session:
            await session.close()


async def search_openalex(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """Search OpenAlex REST API. Free, no API key required."""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": limit,
        "select": "title,authorships,publication_year,doi,id,cited_by_count,abstract_inverted_index",
    }
    headers = {"User-Agent": "GenResearch/0.2.0 (mailto:research@genresearch.dev)"}

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=API_TIMEOUT)

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("openalex_error", extra={"status": resp.status})
                return {"status": "error", "error": f"HTTP {resp.status}", "results": []}
            data = await resp.json()

        results = []
        for work in data.get("results", []):
            authors = ", ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (work.get("authorships") or [])[:5]
            )
            doi = work.get("doi", "") or ""
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]

            # Reconstruct abstract from inverted index when available
            abstract = ""
            inv_index = work.get("abstract_inverted_index")
            if inv_index:
                try:
                    max_pos = max(pos for positions in inv_index.values() for pos in positions)
                    words = [""] * (max_pos + 1)
                    for word, positions in inv_index.items():
                        for pos in positions:
                            words[pos] = word
                    abstract = " ".join(w for w in words if w)
                except Exception:
                    abstract = ""

            results.append({
                "title": work.get("title", "Unknown") or "Unknown",
                "authors": authors,
                "year": work.get("publication_year"),
                "url": work.get("id", ""),
                "doi": doi,
                "abstract_snippet": abstract[:ABSTRACT_SNIPPET_LENGTH],
                "citation_count": work.get("cited_by_count", 0),
                "source_api": "openalex",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return {"status": "success", "results": results}

    except asyncio.TimeoutError:
        logger.warning("openalex_timeout")
        return {"status": "timeout", "results": []}
    except Exception as e:
        logger.warning("openalex_exception", extra={"error": str(e)})
        return {"status": "error", "error": str(e), "results": []}
    finally:
        if own_session:
            await session.close()


async def search_arxiv(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """Search arXiv for preprints via their Atom API."""
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
                return {"status": "error", "error": f"HTTP {resp.status}", "results": []}
            text = await resp.text()

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
            link = ""
            for lnk in entry.findall("atom:link", ns):
                if lnk.get("type") == "text/html":
                    link = lnk.get("href", "")
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
                "abstract_snippet": ((summary_el.text or "").strip()[:ABSTRACT_SNIPPET_LENGTH]) if summary_el is not None else "",
                "source_api": "arxiv",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return {"status": "success", "results": results}

    except asyncio.TimeoutError:
        logger.warning("arxiv_timeout")
        return {"status": "timeout", "results": []}
    except Exception as e:
        logger.warning("arxiv_exception", extra={"error": str(e)})
        return {"status": "error", "error": str(e), "results": []}
    finally:
        if own_session:
            await session.close()


# ──────────────────────────────────────────────────────────
# Core gathering logic
# ──────────────────────────────────────────────────────────

async def _gather_one_gap(
    gap: dict,
    existing_titles: set[str],
    sources_per_gap: int,
    session: aiohttp.ClientSession,
    errors: list[str],
) -> list[dict]:
    """
    Fetch sources for a single gap by querying all APIs concurrently.
    Deduplicates against existing_titles (shared mutable set — caller holds lock).
    """
    query = gap.get("search_query") or gap.get("topic", "")
    if not query:
        return []

    # Fire all APIs concurrently — wall time = slowest API, not sum
    ss_task, cr_task, oa_task, ax_task = await asyncio.gather(
        search_semantic_scholar(query, limit=sources_per_gap, session=session),
        search_crossref(query, limit=sources_per_gap, session=session),
        search_openalex(query, limit=sources_per_gap, session=session),
        search_arxiv(query, limit=sources_per_gap, session=session),
        return_exceptions=True,
    )

    gap_sources: list[dict] = []

    for api_result in (ss_task, cr_task, oa_task, ax_task):
        if isinstance(api_result, Exception):
            errors.append(str(api_result))
            continue
        if api_result.get("status") == "error":
            errors.append(api_result.get("error", "unknown error"))
        for source in api_result.get("results", []):
            title_key = _title_key(source.get("title"))
            if title_key and title_key not in existing_titles:
                source["gap_topic"] = gap.get("topic", "")
                if gap.get("source_category"):
                    source["source_category"] = gap["source_category"]
                gap_sources.append(source)
                existing_titles.add(title_key)
            if len(gap_sources) >= sources_per_gap:
                break
        if len(gap_sources) >= sources_per_gap:
            break

    return gap_sources


async def gather_sources_for_gaps(
    gaps: list[dict],
    existing_sources: list[dict] | None = None,
    sources_per_gap: int = 3,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Gap-driven source gathering. All gaps processed concurrently
    (bounded by _GAP_CONCURRENCY semaphore). All APIs queried in
    parallel per gap.

    Returns:
        (found_sources, unfilled_gaps, errors)
    """
    started_at = time.perf_counter()
    existing_titles: set[str] = {
        _title_key(s.get("title"))
        for s in (existing_sources or [])
        if _title_key(s.get("title"))
    }

    all_found: list[dict] = []
    unfilled: list[dict] = []
    errors: list[str] = []

    sem = asyncio.Semaphore(_GAP_CONCURRENCY)

    async def bounded_gather(gap: dict, session: aiohttp.ClientSession) -> tuple[dict, list[dict]]:
        async with sem:
            sources = await _gather_one_gap(gap, existing_titles, sources_per_gap, session, errors)
            return gap, sources

    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        tasks = [bounded_gather(gap, session) for gap in gaps if gap.get("search_query") or gap.get("topic")]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in results:
        if isinstance(item, Exception):
            errors.append(str(item))
            continue
        gap, sources = item
        if sources:
            all_found.extend(sources)
        else:
            unfilled.append(gap)

    # Gaps without a query string
    for gap in gaps:
        if not (gap.get("search_query") or gap.get("topic")):
            unfilled.append(gap)

    logger.info(
        "source_gathering_complete",
        extra={
            "gaps_searched": len(gaps),
            "sources_found": len(all_found),
            "unfilled_gaps": len(unfilled),
            "errors": len(errors),
            "request_count": sum(
                4 for gap in gaps if gap.get("search_query") or gap.get("topic")
            ),
            "duration_s": round(time.perf_counter() - started_at, 2),
        },
    )
    return all_found, unfilled, errors
