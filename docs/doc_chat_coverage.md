# Document chat coverage

This project adds a purely additive document-structure layer for whole-document, deterministic coverage analysis.

## Architecture

- `services/doc_structure/`: extraction and persistence helpers for page text, references, sections, tables/figures, and the paper-type classifier.
- `services/doc_chat/`: intent routing and deterministic handlers for citations, section lists, item lists, and question answering.
- `routers/doc_structure.py`: rebuild and introspection endpoints for per-paper structure state.
- `supabase/migrations/20261008_doc_structure.sql`: optional new data model for document structure.

## Flags

- `DOC_STRUCTURE_ON_UPLOAD`: default `True`. When set to `False`, upload behavior reverts to the legacy flow.
- `CHAT_INTENT_ROUTING`: default `True`. When set to `False`, `/chat/ask` and `/chat/ask-stream` follow the old RAG path exactly.

## Coverage metrics

The document-structure tables keep the following measured values:

- `reference_count`: parsed references.
- `expected_reference_count`: highest numbered reference seen or inferred from the references list.
- `missing_reference_ids`: IDs that could not be verified.
- `section_count`: number of detected sections.
- `body_char_coverage`: coverage ratio for the body text against the detected section windows.

The system reports measured coverage honestly and never claims `100%` unless the numbers match exactly.

## Endpoints

- `POST /papers/{paper_id}/structure/rebuild`
- `GET /papers/{paper_id}/structure`
- `GET /papers/{paper_id}/references?format=json|bibtex|ris|csv`

## Known limits

- Scanned PDFs without a usable text layer will report `no_text_layer` and cannot show reliable reference counts without OCR.
- Highly irregular author-year formats or non-standard bibliography layouts may require partial extraction; the system reports the actual percent and missing IDs instead of claiming completeness.
- Live LLM quality metrics for map-reduce evidence and JSON compliance depend on a reachable Ollama instance.
