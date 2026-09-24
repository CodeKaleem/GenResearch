GenResearch: Intelligent Multi-Agent Platform for Academic Research Assistance.

## Research pipeline implementation

The backend now includes the plan's typed research contracts and quality path:

- provenance-aware PDF parsing, cleanup, optional table extraction, and deterministic chunk IDs;
- section-targeted retrieval with reciprocal-rank fusion over the existing Chroma store;
- claim extraction, evidence-tag hard gates, verification verdicts, and generated-claim audit records;
- sequential section composition, redundancy detection, citation registry linting, and human-input checks;
- constrained chart execution, DOCX assembly, quality scorers, and fixture evaluation;
- VRAM-aware Ollama role routing with configurable context budgets and model-call audit records.

Install backend dependencies with `backend/.venv/bin/pip install -r backend/requirements.txt`.
Set `OLLAMA_HEAVY_MODEL`, `OLLAMA_MID_MODEL`, and `OLLAMA_LIGHT_MODEL` in `backend/.env` when the locally pulled model names differ from the Qwen/Phi defaults. Apply `supabase/migrations/20260923_grounding_audit.sql` before running the verification audit path.

The current vector backend remains Chroma for compatibility with the existing application. Qdrant, a CPU cross-encoder reranker, and Docker-level isolation for generated chart code are production upgrade paths; the chart service already enforces an import/AST allowlist and process timeout for local development.

## Paper discovery

Authenticated users can open **Find Papers** in the dashboard to search by topic or upload a PDF for related-paper discovery. The frontend calls `POST /search-papers`, which queries Semantic Scholar, arXiv, Crossref, and OpenAlex, then deduplicates and ranks the results.
