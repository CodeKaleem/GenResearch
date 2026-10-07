from __future__ import annotations

from database.supabase_client import get_supabase


async def handle_sections_list(user_id: str, *, paper_id: str | None = None):
    sb = get_supabase()
    query = sb.table("paper_sections").select("*").eq("user_id", user_id)
    if paper_id:
        query = query.eq("paper_id", paper_id)
    result = query.order("ordinal", desc=False).execute()
    sections = result.data or []
    lines = [f"{section['ordinal']}. {section['title']} (p. {section['page_start']}-{section['page_end']})" for section in sections]
    answer = "\n".join(lines) if lines else "No section structure is available yet."
    return {
        "answer": answer,
        "sources": [],
        "chunks_used": 0,
        "model": "doc-structure",
        "intent": "sections_list",
        "coverage": {"unit": "sections", "covered": len(sections), "total": len(sections), "percent": 100.0 if sections else 0.0, "missing": []},
        "items": None,
    }
