"""Modular Web Scraping Pipeline for FYP Academic Paper Collector.

Provides multi-source academic paper metadata extraction as a resilient fallback
for API-key-restricted endpoints across 4 primary scholarly repositories:
1. arXiv (Static HTML parsing via requests + BeautifulSoup4)
2. Crossref (Static HTML parsing via requests + BeautifulSoup4)
3. Semantic Scholar (Dynamic SPA parsing via Playwright async API)
4. OpenAlex (Dynamic SPA parsing via Playwright async API)

Architecture Highlights:
- Unified normalized data schema matching specification.
- Asynchronous parallel execution engine (asyncio.gather).
- Defensive fault isolation per source (try/except wrapper per scraper).
- Local SHA-256 JSON caching layer (mock_cache/) for live supervisor demos.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import re
from typing import Any, List, Optional
import urllib.parse

from bs4 import BeautifulSoup
import requests

# Set up dedicated logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("ScrapingEngine")

# Cache directory configuration (default to mock_cache relative to backend root)
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "mock_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Realistic User-Agent pool for rotating request headers and Playwright contexts
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


def _get_random_user_agent() -> str:
    """Return a randomized modern desktop user agent."""
    return random.choice(USER_AGENTS)


def normalize_paper_record(
    source: str,
    title: str,
    authors: List[str],
    abstract: str,
    url: str,
    publication_date: str,
) -> dict[str, Any]:
    """Normalize paper metadata into the unified FYP dictionary schema."""
    cleaned_authors = [
        re.sub(r"\s+", " ", str(a)).strip()
        for a in (authors or [])
        if re.sub(r"\s+", " ", str(a)).strip()
    ]

    cleaned_title = re.sub(r"\s+", " ", str(title or "")).strip()
    cleaned_abstract = re.sub(r"\s+", " ", str(abstract or "")).strip()[:1500]
    cleaned_url = str(url or "").strip()
    cleaned_date = str(publication_date or "").strip()

    return {
        "source": source,
        "title": cleaned_title,
        "authors": cleaned_authors,
        "abstract": cleaned_abstract,
        "url": cleaned_url,
        "publication_date": cleaned_date,
    }


# =====================================================================
# Caching Layer (mock_cache/)
# =====================================================================
def get_query_hash(query: str) -> str:
    """Generate SHA-256 hash for query string normalization."""
    normalized_q = query.strip().lower()
    return hashlib.sha256(normalized_q.encode("utf-8")).hexdigest()


def get_cached_results(query: str) -> Optional[List[dict[str, Any]]]:
    """Retrieve locally cached scraping results for query if available."""
    q_hash = get_query_hash(query)
    cache_file = CACHE_DIR / f"{q_hash}.json"

    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
                results = payload.get("results")
                if isinstance(results, list):
                    logger.info(
                        f"[CACHE HIT] Returning {len(results)} cached papers for '{query}' (hash={q_hash[:10]}...)"
                    )
                    return results
        except Exception as exc:
            logger.warning(f"[CACHE READ ERROR] Failed to read {cache_file}: {exc}")
    return None


def save_cached_results(query: str, results: List[dict[str, Any]]) -> None:
    """Save valid scraping results into the local mock_cache directory."""
    if not results:
        return
    q_hash = get_query_hash(query)
    cache_file = CACHE_DIR / f"{q_hash}.json"
    payload = {
        "query": query.strip(),
        "query_hash": q_hash,
        "cached_at": datetime.utcnow().isoformat() + "Z",
        "total_results": len(results),
        "results": results,
    }
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(
            f"[CACHE SAVED] Cached {len(results)} papers for '{query}' -> {cache_file.name}"
        )
    except Exception as exc:
        logger.error(f"[CACHE WRITE ERROR] Failed to save {cache_file}: {exc}")


# =====================================================================
# 1. arXiv Scraper (Static HTML: requests + BeautifulSoup4)
# =====================================================================
def _parse_arxiv_date(raw_text: str) -> str:
    """Extract and format publication date from arXiv result text."""
    if not raw_text:
        return ""
    m_full = re.search(r"Submitted\s*([0-9]{1,2}\s+[A-Za-z]+,\s*[0-9]{4})", raw_text)
    if m_full:
        date_str = m_full.group(1)
        for fmt in ("%d %B, %Y", "%d %b, %Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return date_str
    m_year = re.search(r"\b(19\d\d|20\d\d)\b", raw_text)
    return m_year.group(1) if m_year else ""


def _scrape_arxiv_sync(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Synchronous parsing logic for arXiv search results."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://arxiv.org/search/?query={encoded_query}&searchtype=all"
    headers = {"User-Agent": _get_random_user_agent()}

    logger.info(f"[arXiv] Fetching static HTML from: {url}")
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    result_nodes = soup.find_all("li", class_="arxiv-result")

    papers: List[dict[str, Any]] = []
    for node in result_nodes[:max_results]:
        # Title extraction: <p class="title">
        title_elem = node.find("p", class_="title")
        raw_title = title_elem.get_text(separator=" ", strip=True) if title_elem else ""
        clean_title = re.sub(r"^(Title:\s*|title:\s*)", "", raw_title, flags=re.IGNORECASE).strip()

        # Authors extraction: <p class="authors"><a>...</a></p>
        authors_elem = node.find("p", class_="authors")
        authors = (
            [a.get_text(strip=True) for a in authors_elem.find_all("a")]
            if authors_elem
            else []
        )

        # Abstract extraction: <span class="abstract-full"> with fallback
        abs_elem = node.find("span", class_="abstract-full") or node.find(
            "span", class_="abstract-short"
        )
        raw_abs = abs_elem.get_text(separator=" ", strip=True) if abs_elem else ""
        raw_abs = re.sub(r"^(Abstract:\s*|abstract:\s*)", "", raw_abs, flags=re.IGNORECASE).strip()
        # Strip trailing pagination/expand toggles e.g. "△ Less"
        clean_abs = re.sub(r"[\s△▲]+(?:Less|More)\s*$", "", raw_abs, flags=re.IGNORECASE).strip()

        # URL extraction
        link_elem = node.find("a", href=lambda h: h and "arxiv.org/abs/" in h)
        paper_url = link_elem["href"].strip() if link_elem else ""

        # Publication date extraction
        date_elem = node.find("p", class_="is-size-7")
        pub_date = _parse_arxiv_date(date_elem.get_text(strip=True) if date_elem else "")

        if clean_title:
            papers.append(
                normalize_paper_record(
                    source="arXiv",
                    title=clean_title,
                    authors=authors,
                    abstract=clean_abs,
                    url=paper_url,
                    publication_date=pub_date,
                )
            )

    logger.info(f"[arXiv] Successfully parsed {len(papers)} papers")
    return papers


async def scrape_arxiv(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Scrape arXiv academic papers asynchronously."""
    try:
        return await asyncio.to_thread(_scrape_arxiv_sync, query, max_results)
    except Exception as exc:
        logger.error(f"[arXiv] Scraping failed for '{query}': {exc}", exc_info=True)
        return []


# =====================================================================
# 2. Crossref Scraper (Static HTML: requests + BeautifulSoup4)
# =====================================================================
def _scrape_crossref_sync(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Synchronous parsing logic for Crossref search results."""
    encoded_query = urllib.parse.quote(query)
    # Target Crossref web interface with search parameters
    url = f"https://search.crossref.org/?q={encoded_query}&from_ui=yes"
    headers = {
        "User-Agent": _get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    logger.info(f"[Crossref] Fetching static HTML from: {url}")
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")

    papers: List[dict[str, Any]] = []
    for row in rows:
        lead_elem = row.find("p", class_="lead")
        if not lead_elem:
            continue
        clean_title = lead_elem.get_text(separator=" ", strip=True)

        # Extract authors from <p class="expand">
        expand_elem = row.find("p", class_="expand")
        authors: List[str] = []
        if expand_elem:
            auth_raw = expand_elem.get_text(strip=True)
            auth_raw = re.sub(r"^Authors?:\s*", "", auth_raw, flags=re.IGNORECASE).strip()
            if auth_raw:
                authors = [a.strip() for a in auth_raw.split(",") if a.strip()]

        # Extract URL / DOI link
        link_elem = row.find("a", href=lambda h: h and ("doi.org" in h or "http" in h))
        paper_url = link_elem["href"].strip() if link_elem else ""

        # Extract date from <p class="extra">
        extra_elem = row.find("p", class_="extra")
        pub_date = ""
        if extra_elem:
            m_year = re.search(r"\b(19\d\d|20\d\d)\b", extra_elem.get_text())
            if m_year:
                pub_date = m_year.group(1)

        # Handle missing abstracts gracefully as specified
        abstract = ""

        if clean_title:
            papers.append(
                normalize_paper_record(
                    source="Crossref",
                    title=clean_title,
                    authors=authors,
                    abstract=abstract,
                    url=paper_url,
                    publication_date=pub_date,
                )
            )
            if len(papers) >= max_results:
                break

    logger.info(f"[Crossref] Successfully parsed {len(papers)} papers")
    return papers


async def scrape_crossref(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Scrape Crossref academic papers asynchronously."""
    try:
        return await asyncio.to_thread(_scrape_crossref_sync, query, max_results)
    except Exception as exc:
        logger.error(f"[Crossref] Scraping failed for '{query}': {exc}", exc_info=True)
        return []


# =====================================================================
# 3. Semantic Scholar Scraper (Dynamic SPA: Playwright async_api)
# =====================================================================
async def scrape_semantic_scholar(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Dynamic SPA scraper for Semantic Scholar using Playwright."""
    from playwright.async_api import async_playwright

    encoded_query = urllib.parse.quote(query)
    url = f"https://www.semanticscholar.org/search?q={encoded_query}"
    user_agent = _get_random_user_agent()

    logger.info(f"[SemanticScholar] Launching browser context for: {url}")
    papers: List[dict[str, Any]] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                ],
            )
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            # Navigate and delay for basic bot mitigation
            await page.goto(url, timeout=25000, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

            # Wait for React hydration
            try:
                await page.wait_for_selector(
                    '[data-test-id="paper-tile-title"]', timeout=8000
                )
            except Exception as wait_err:
                logger.warning(
                    f"[SemanticScholar] Tile selector wait timed out or challenged: {wait_err}"
                )

            # Extract paper cards
            card_data = await page.evaluate(
                """() => {
                const results = [];
                const cards = document.querySelectorAll('[data-test-id="paper-tile-title"]');
                cards.forEach(titleEl => {
                    const card = titleEl.closest('article') || titleEl.closest('.cl-paper-row') || titleEl.closest('div');
                    const title = titleEl.innerText.trim();
                    const url = titleEl.href || (titleEl.querySelector('a') ? titleEl.querySelector('a').href : '');
                    
                    let authors = [];
                    if (card) {
                        const authorLinks = card.querySelectorAll('[data-test-id="author-list"] a, .author-list a, .cl-paper-authors a');
                        if (authorLinks.length > 0) {
                            authorLinks.forEach(a => authors.push(a.innerText.trim()));
                        }
                    }
                    
                    let abstract = '';
                    if (card) {
                        const absEl = card.querySelector('[data-test-id="abstract-text"], .tldr-abstract, .cl-paper-abstract');
                        if (absEl) abstract = absEl.innerText.trim();
                    }
                    
                    let year = '';
                    if (card) {
                        const text = card.innerText;
                        const match = text.match(/\\b(19\\d\\d|20\\d\\d)\\b/);
                        if (match) year = match[1];
                    }
                    
                    if (title) {
                        results.push({
                            title: title,
                            authors: authors,
                            abstract: abstract,
                            url: url,
                            publication_date: year
                        });
                    }
                });
                return results;
            }"""
            )

            await browser.close()

            for item in (card_data or [])[:max_results]:
                papers.append(
                    normalize_paper_record(
                        source="SemanticScholar",
                        title=item.get("title", ""),
                        authors=item.get("authors", []),
                        abstract=item.get("abstract", ""),
                        url=item.get("url", ""),
                        publication_date=item.get("publication_date", ""),
                    )
                )

            logger.info(f"[SemanticScholar] Extracted {len(papers)} paper entries")
            return papers

    except Exception as exc:
        logger.warning(f"[SemanticScholar] Scraper error for '{query}': {exc}")
        return []


# =====================================================================
# 4. OpenAlex Scraper (Dynamic SPA: Playwright async_api)
# =====================================================================
async def scrape_openalex(query: str, max_results: int = 10) -> List[dict[str, Any]]:
    """Dynamic SPA scraper for OpenAlex web interface using Playwright."""
    from playwright.async_api import async_playwright

    encoded_query = urllib.parse.quote(query)
    url = f"https://openalex.org/works?search={encoded_query}"
    user_agent = _get_random_user_agent()

    logger.info(f"[OpenAlex] Launching browser context for: {url}")
    papers: List[dict[str, Any]] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            # Wait for search result DOM
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(2.0)

            # Extract card texts directly from DOM
            extracted_items = await page.evaluate(
                """() => {
                const results = [];
                // Look for work cards or work links
                const links = document.querySelectorAll('a[href*="/works/W"], .work-title, .v-card');
                const seenTitles = new Set();
                
                links.forEach(el => {
                    const card = el.closest('.v-card') || el.closest('tr') || el;
                    const text = card.innerText || '';
                    const titleEl = card.querySelector('a[href*="/works/W"], .work-title') || el;
                    const title = titleEl ? titleEl.innerText.trim() : '';
                    const href = titleEl ? titleEl.href : '';
                    
                    if (title && !seenTitles.has(title)) {
                        seenTitles.add(title);
                        
                        let year = '';
                        const yearMatch = text.match(/\\b(19\\d\\d|20\\d\\d)\\b/);
                        if (yearMatch) year = yearMatch[1];
                        
                        let authors = [];
                        const authorEl = card.querySelector('.authors, .v-card-subtitle');
                        if (authorEl) {
                            authors = authorEl.innerText.split(',').map(s => s.trim()).filter(Boolean);
                        }
                        
                        results.push({
                            title: title,
                            authors: authors,
                            abstract: '',
                            url: href,
                            publication_date: year
                        });
                    }
                });
                return results;
            }"""
            )

            await browser.close()

            for item in (extracted_items or [])[:max_results]:
                papers.append(
                    normalize_paper_record(
                        source="OpenAlex",
                        title=item.get("title", ""),
                        authors=item.get("authors", []),
                        abstract=item.get("abstract", ""),
                        url=item.get("url", ""),
                        publication_date=item.get("publication_date", ""),
                    )
                )

            logger.info(f"[OpenAlex] Extracted {len(papers)} paper entries")
            return papers

    except Exception as exc:
        logger.warning(f"[OpenAlex] Scraper error for '{query}': {exc}")
        return []


# =====================================================================
# Parallel Execution Engine & Orchestrator
# =====================================================================
async def scrape_all_sources(
    query: str,
    use_cache: bool = True,
    max_results_per_source: int = 10,
) -> List[dict[str, Any]]:
    """Asynchronously scrape all 4 sources concurrently with defensive fallback.

    Args:
        query: Search keywords or research question.
        use_cache: If True, returns instant local cached results if available.
        max_results_per_source: Max items to retain per individual scholarly source.

    Returns:
        List of normalized paper dictionaries across active sources.
    """
    clean_query = query.strip()
    if not clean_query:
        logger.warning("Empty query provided to scrape_all_sources.")
        return []

    # 1. Caching Check (Instant response for supervisor demos)
    if use_cache:
        cached = get_cached_results(clean_query)
        if cached is not None:
            return cached

    logger.info(
        f"[ORCHESTRATOR] Starting concurrent multi-source scrape for: '{clean_query}'"
    )

    # 2. Parallel Concurrent Execution (asyncio.gather)
    tasks = [
        scrape_arxiv(clean_query, max_results=max_results_per_source),
        scrape_crossref(clean_query, max_results=max_results_per_source),
        scrape_semantic_scholar(clean_query, max_results=max_results_per_source),
        scrape_openalex(clean_query, max_results=max_results_per_source),
    ]

    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    sources = ["arXiv", "Crossref", "SemanticScholar", "OpenAlex"]
    combined_results: List[dict[str, Any]] = []

    for source_name, outcome in zip(sources, task_results):
        if isinstance(outcome, Exception):
            logger.error(
                f"[ORCHESTRATOR] Source '{source_name}' raised an unhandled exception: {outcome}"
            )
            continue
        if isinstance(outcome, list):
            logger.info(
                f"[ORCHESTRATOR] Source '{source_name}' contributed {len(outcome)} papers"
            )
            combined_results.extend(outcome)

    # 3. Save to local mock_cache if results were acquired
    if combined_results:
        save_cached_results(clean_query, combined_results)
    else:
        logger.warning(
            f"[ORCHESTRATOR] No results were scraped across any source for '{clean_query}'"
        )

    return combined_results


# =====================================================================
# CLI Demo Test Snippet
# =====================================================================
if __name__ == "__main__":
    import sys

    demo_query = sys.argv[1] if len(sys.argv) > 1 else "Graph Neural Networks"

    print("=" * 80)
    print(f"FYP Academic Paper Collector — Multi-Source Scraping Pipeline Demo")
    print(f"Target Query: '{demo_query}'")
    print("=" * 80)

    results = asyncio.run(scrape_all_sources(demo_query, use_cache=True))

    print("\n" + "-" * 80)
    print(f"Total Papers Aggregated: {len(results)}")
    print("-" * 80)

    # Print summary breakdown by source
    counts: dict[str, int] = {}
    for paper in results:
        counts[paper["source"]] = counts.get(paper["source"], 0) + 1

    for src, count in sorted(counts.items()):
        print(f"  • {src:<16}: {count} papers")

    print("\nSample Extracted Records (First 3):")
    for idx, paper in enumerate(results[:3], start=1):
        print(f"\n[{idx}] [{paper['source']}] {paper['title']}")
        print(f"    Authors : {', '.join(paper['authors'][:4]) if paper['authors'] else 'N/A'}")
        print(f"    Date    : {paper['publication_date'] or 'N/A'}")
        print(f"    URL     : {paper['url']}")
        print(f"    Abstract: {paper['abstract'][:180]}..." if paper['abstract'] else "    Abstract: [None]")
    print("\n" + "=" * 80)
