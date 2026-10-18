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
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional

import aiohttp

from config import settings
from services.scraping_engine import scrape_all_sources

logger = logging.getLogger(__name__)

# Timeout for external API calls
API_TIMEOUT = aiohttp.ClientTimeout(total=30)
ABSTRACT_SNIPPET_LENGTH = 1500


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


async def search_semantic_scholar(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
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
                return {"status": "error", "error": f"Semantic Scholar HTTP {resp.status}", "results": []}
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
                "abstract_snippet": (p.get("abstract") or "")[:ABSTRACT_SNIPPET_LENGTH],
                "citation_count": p.get("citationCount", 0),
                "source_api": "semantic_scholar",
                "accessed_date": datetime.utcnow().isoformat(),
            })
        return {"status": "success", "results": results, "error": ""}

    except Exception as e:
        logger.warning("semantic_scholar_exception", extra={"error": str(e)})
        return {"status": "error", "error": f"Semantic Scholar exception: {str(e)}", "results": []}
    finally:
        if own_session:
            await session.close()


async def search_arxiv(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
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
                return {"status": "error", "error": f"arXiv HTTP {resp.status}", "results": []}
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
                "abstract_snippet": ((summary_el.text or "").strip()[:ABSTRACT_SNIPPET_LENGTH]) if summary_el is not None else "",
                "source_api": "arxiv",
                "accessed_date": datetime.utcnow().isoformat(),
            })

        return {"status": "success", "results": results, "error": ""}

    except Exception as e:
        logger.warning("arxiv_exception", extra={"error": str(e)})
        return {"status": "error", "error": f"arXiv exception: {str(e)}", "results": []}
    finally:
        if own_session:
            await session.close()


async def search_crossref(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """
    Search CrossRef API for DOIs and scholarly works.
    A8: Added to fulfill Priority 3.
    """
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
                return {"status": "error", "error": f"CrossRef HTTP {resp.status}", "results": []}
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
            
            year = _crossref_year(item)
            abstract = _clean_abstract(item.get("abstract") or "")

            results.append({
                "title": title,
                "authors": authors,
                "year": year,
                "url": item.get("URL", ""),
                "doi": item.get("DOI", ""),
                "abstract_snippet": abstract[:ABSTRACT_SNIPPET_LENGTH],
                "citation_count": item.get("is-referenced-by-count", 0),
                "source_api": "crossref",
                "accessed_date": datetime.utcnow().isoformat(),
            })

        return {"status": "success", "results": results, "error": ""}

    except Exception as e:
        logger.warning("crossref_exception", extra={"error": str(e)})
        return {"status": "error", "error": f"CrossRef exception: {str(e)}", "results": []}
    finally:
        if own_session:
            await session.close()


async def search_openalex(
    query: str,
    limit: int = 5,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
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
                return {"status": "error", "error": f"OpenAlex HTTP {resp.status}", "results": []}
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

        return {"status": "success", "results": results, "error": ""}

    except Exception as e:
        logger.warning("openalex_exception", extra={"error": str(e)})
        return {"status": "error", "error": f"OpenAlex exception: {str(e)}", "results": []}
    finally:
        if own_session:
            await session.close()


def _convert_scraped_paper(paper: dict, is_case_study: bool = False) -> dict:
    """Transform a normalized scraping engine paper into the source gathering schema."""
    authors_raw = paper.get("authors") or []
    if isinstance(authors_raw, list):
        authors_str = ", ".join(authors_raw)
    else:
        authors_str = str(authors_raw)

    raw_date = str(paper.get("publication_date") or "")
    year = None
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_date)
    if year_match:
        try:
            year = int(year_match.group(1))
        except (ValueError, TypeError):
            year = None

    url = paper.get("url", "")
    doi = ""
    if "doi.org/" in url:
        doi = url.split("doi.org/")[-1].strip()

    abstract = paper.get("abstract", "") or ""
    source_name = str(paper.get("source", "WebScraper"))

    return {
        "title": paper.get("title", "Unknown"),
        "authors": authors_str or "Unknown",
        "year": year,
        "url": url,
        "doi": doi,
        "abstract_snippet": abstract[:ABSTRACT_SNIPPET_LENGTH],
        "content": abstract,
        "citation_count": 0,
        "source_api": f"scraping_{source_name.lower()}",
        "source_type": "case_study" if is_case_study else "scraped",
        "is_case_study": is_case_study,
        "accessed_date": datetime.utcnow().isoformat(),
    }


async def gather_sources_for_gaps(
    gaps: list[dict],
    existing_sources: list[dict] | None = None,
    sources_per_gap: int = 3,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Gap-driven source gathering.

    Args:
        gaps:            List of gap dicts from the gap report, each with a 'search_query'.
        existing_sources: Sources already available (to avoid duplicates).
        sources_per_gap: Max sources to find per gap.

    Returns:
        (found_sources, unfilled_gaps, errors) — sources found, gaps with no results, and a list of API error messages.
    """
    existing_titles = {
        _title_key(source.get("title"))
        for source in (existing_sources or [])
        if _title_key(source.get("title"))
    }

    all_found: list[dict] = []
    unfilled: list[dict] = []
    errors: list[str] = []

    def add_unique_sources(results: list[dict], gap_sources: list[dict], gap: dict) -> None:
        for source in results:
            title = source.get("title") or "Unknown"
            title_key = _title_key(title)
            if title_key not in existing_titles:
                source["title"] = title
                source["gap_topic"] = gap.get("topic", "")
                gap_sources.append(source)
                existing_titles.add(title_key)

    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        for gap in gaps:
            query = gap.get("search_query") or gap.get("topic", "")
            if not query:
                unfilled.append(gap)
                continue

            gap_sources: list[dict] = []

            # Priority 0: Multi-source Web Scraping Pipeline (arXiv, Crossref, Semantic Scholar, OpenAlex)
            # Provides resilient fallback for API key approval delays, including real-world stories and case studies
            if getattr(settings, "SCRAPER_SOURCE_GATHERING", True):
                try:
                    scraped_papers = await scrape_all_sources(
                        query,
                        use_cache=getattr(settings, "SCRAPER_USE_CACHE", True),
                        max_results_per_source=sources_per_gap,
                    )
                    if scraped_papers:
                        converted = [_convert_scraped_paper(p, is_case_study=False) for p in scraped_papers]
                        add_unique_sources(converted, gap_sources, gap)

                    # Gather real-world stories, examples, and empirical case studies if enabled
                    if getattr(settings, "SCRAPER_ENABLE_CASE_STUDIES", True) and len(gap_sources) < sources_per_gap:
                        case_query = f"{query} case study practical application"
                        case_papers = await scrape_all_sources(
                            case_query,
                            use_cache=getattr(settings, "SCRAPER_USE_CACHE", True),
                            max_results_per_source=max(1, sources_per_gap - len(gap_sources)),
                        )
                        if case_papers:
                            converted_cases = [_convert_scraped_paper(p, is_case_study=True) for p in case_papers]
                            add_unique_sources(converted_cases, gap_sources, gap)
                except Exception as scrap_exc:
                    logger.warning("scraping_pipeline_exception", extra={"error": str(scrap_exc), "query": query})
                    errors.append(f"Scraping error: {str(scrap_exc)}")

            # Priority 1: Semantic Scholar (Fallback if scraping pipeline didn't fill the gap)
            if len(gap_sources) < sources_per_gap:
                res = await search_semantic_scholar(query, limit=sources_per_gap - len(gap_sources), session=session)
                if res["status"] == "error":
                    errors.append(res["error"])
                add_unique_sources(res["results"], gap_sources, gap)

            # Priority 2: arXiv (if Semantic Scholar didn't fill the gap)
            if len(gap_sources) < sources_per_gap:
                remaining = sources_per_gap - len(gap_sources)
                res = await search_arxiv(query, limit=remaining, session=session)
                if res["status"] == "error":
                    errors.append(res["error"])
                add_unique_sources(res["results"], gap_sources, gap)
                        
            # Priority 3: CrossRef (A8)
            if len(gap_sources) < sources_per_gap:
                remaining = sources_per_gap - len(gap_sources)
                res = await search_crossref(query, limit=remaining, session=session)
                if res["status"] == "error":
                    errors.append(res["error"])
                add_unique_sources(res["results"], gap_sources, gap)

            # Priority 4: OpenAlex (if still not enough)
            if len(gap_sources) < sources_per_gap:
                remaining = sources_per_gap - len(gap_sources)
                res = await search_openalex(query, limit=remaining, session=session)
                if res["status"] == "error":
                    errors.append(res["error"])
                add_unique_sources(res["results"], gap_sources, gap)

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
            "errors": len(errors),
        },
    )

    return all_found, unfilled, errors
