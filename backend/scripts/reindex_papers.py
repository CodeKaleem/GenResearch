"""Re-chunk and re-embed already uploaded papers with the current settings.

Run this after changing any of: CHUNK_SIZE, CHUNK_OVERLAP, OLLAMA_EMBED_MODEL,
OLLAMA_EMBED_PREFIXES. Vectors made with the old settings are not comparable with
new query vectors, so retrieval quality is poor until papers are re-indexed.

New chunks are written first and old chunk ids are removed afterwards, so a paper
is never left empty if the run is interrupted.

    cd backend
    python -m scripts.reindex_papers --dry-run
    python -m scripts.reindex_papers                      # every paper
    python -m scripts.reindex_papers --user-id <uuid>     # one user
    python -m scripts.reindex_papers --paper-id <uuid>    # one paper
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database.chroma_client import get_user_collection  # noqa: E402
from database.supabase_client import get_supabase  # noqa: E402
from ingestion import chunk_document, parse_pdf  # noqa: E402
from ingestion.pdf_parser import ParsedBlock  # noqa: E402
from ingestion.table_extractor import extract_tables  # noqa: E402
from services.chroma_service import store_chunks, store_structured_chunks  # noqa: E402
from services.chunker import chunk_text  # noqa: E402
from services.pdf_extractor import extract_text_from_pdf  # noqa: E402


async def reindex_paper(paper: dict, dry_run: bool) -> str:
    user_id, paper_id = paper["user_id"], paper["id"]
    title = paper.get("title") or "Untitled"
    path = paper.get("storage_path")
    if not path or not os.path.exists(path):
        return "skipped (PDF file not found on disk)"

    file_bytes = Path(path).read_bytes()
    text = await extract_text_from_pdf(file_bytes)
    if not text.strip():
        return "skipped (no extractable text)"

    blocks = await asyncio.to_thread(parse_pdf, file_bytes)
    blocks.extend(
        ParsedBlock(
            text=f"Table {t['table']} on page {t['page']}: {t['rows']}",
            page=t["page"],
            section_heading=f"Table {t['table']}",
            is_table=True,
            table_data={"rows": t["rows"]},
        )
        for t in await asyncio.to_thread(extract_tables, file_bytes)
    )
    structured = chunk_document(blocks, paper_id, title)
    collection_name = paper.get("collection") or "default"

    col = get_user_collection(user_id)
    old_ids = set((col.get(where={"paper_id": paper_id}, include=[]).get("ids")) or [])

    if dry_run:
        n = len(structured) if structured else len(chunk_text(text))
        return f"would replace {len(old_ids)} chunks with {n}"

    if structured:
        stored = await store_structured_chunks(user_id=user_id, chunks=structured, collection_name=collection_name)
        new_ids = {meta.chunk_id for meta, _ in structured}
    else:
        pieces = chunk_text(text)
        stored = await store_chunks(user_id=user_id, paper_id=paper_id, chunks=pieces, title=title, collection_name=collection_name)
        new_ids = {f"{paper_id}_chunk_{i}" for i in range(len(pieces))}

    stale = list(old_ids - new_ids)
    for i in range(0, len(stale), 500):
        col.delete(ids=stale[i : i + 500])
    get_supabase().table("papers").update({"chunks": stored}).eq("id", paper_id).execute()
    return f"replaced {len(old_ids)} chunks with {stored}"


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id")
    parser.add_argument("--paper-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        f"Settings: CHUNK_SIZE={settings.CHUNK_SIZE} CHUNK_OVERLAP={settings.CHUNK_OVERLAP} "
        f"EMBED_MODEL={settings.OLLAMA_EMBED_MODEL} EMBED_PREFIXES={settings.OLLAMA_EMBED_PREFIXES}"
    )
    query = get_supabase().table("papers").select("id, user_id, title, storage_path, collection")
    if args.user_id:
        query = query.eq("user_id", args.user_id)
    if args.paper_id:
        query = query.eq("id", args.paper_id)
    papers = query.execute().data or []
    print(f"{len(papers)} paper(s) to process{' (dry run)' if args.dry_run else ''}")

    for index, paper in enumerate(papers, 1):
        try:
            result = await reindex_paper(paper, args.dry_run)
        except Exception as exc:  # keep going; report at the end
            result = f"FAILED: {exc}"
        print(f"[{index}/{len(papers)}] {paper.get('title', paper['id'])}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
