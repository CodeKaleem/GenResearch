from __future__ import annotations

import asyncio
import os
import sys

from database.supabase_client import get_supabase
from services.doc_structure.pipeline import extract_structure, persist_structure


async def main(user_id: str | None = None) -> None:
    sb = get_supabase()
    query = sb.table("papers").select("id, user_id, storage_path").order("created_at", desc=False)
    if user_id:
        query = query.eq("user_id", user_id)
    rows = query.execute().data or []
    for paper in rows:
        storage_path = paper.get("storage_path")
        if not storage_path or not os.path.exists(storage_path):
            continue
        try:
            with open(storage_path, "rb") as handle:
                pdf_bytes = handle.read()
            structure = await asyncio.to_thread(extract_structure, pdf_bytes)
            await persist_structure(paper["user_id"], paper["id"], structure)
            print(f"Backfilled {paper['id']} ({structure.reference_count} refs)")
        except Exception as exc:
            print(f"Failed {paper['id']}: {exc}")


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(user_id=user_id))
