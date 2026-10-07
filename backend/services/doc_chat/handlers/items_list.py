from __future__ import annotations

from database.supabase_client import get_supabase


async def handle_items_list(user_id: str, *, paper_id: str | None = None):
    sb = get_supabase()
    query = sb.table("paper_items").select("*").eq("user_id", user_id)
    if paper_id:
        query = query.eq("paper_id", paper_id)
    result = query.execute()
    items = result.data or []
    lines = [f"{item['kind']}: {item['label']} (p. {item['page']}) - {item['caption']}" for item in items]
    answer = "\n".join(lines) if lines else "No tables or figures were detected."
    return {
        "answer": answer,
        "sources": [],
        "chunks_used": 0,
        "model": "doc-structure",
        "intent": "items_list",
        "coverage": {"unit": "items", "covered": len(items), "total": len(items), "percent": 100.0 if items else 0.0, "missing": []},
        "items": None,
    }
