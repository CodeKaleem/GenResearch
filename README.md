GenResearch: Intelligent Multi-Agent Platform for Academic Research Assistance.

## Paper discovery

Authenticated users can open **Find Papers** in the dashboard to search by topic or upload a PDF for related-paper discovery. The frontend calls `POST /search-papers`, which queries Semantic Scholar, arXiv, Crossref, and OpenAlex, then deduplicates and ranks the results.
