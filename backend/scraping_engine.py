"""Scraping Engine root entry point for FYP Academic Paper Collector."""
import sys
from pathlib import Path

# Ensure services module is discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.scraping_engine import (
    scrape_all_sources,
    scrape_arxiv,
    scrape_crossref,
    scrape_semantic_scholar,
    scrape_openalex,
    get_cached_results,
    save_cached_results,
    normalize_paper_record,
)

if __name__ == "__main__":
    import asyncio

    demo_query = sys.argv[1] if len(sys.argv) > 1 else "Graph Neural Networks"

    print("=" * 80)
    print("FYP Academic Paper Collector — Multi-Source Scraping Pipeline Demo")
    print(f"Target Query: '{demo_query}'")
    print("=" * 80)

    results = asyncio.run(scrape_all_sources(demo_query, use_cache=True))

    print("\n" + "-" * 80)
    print(f"Total Papers Aggregated: {len(results)}")
    print("-" * 80)

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
