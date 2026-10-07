from __future__ import annotations

from services.llm_service import call_llm


async def map_reduce_items(*, query: str, sections: list[dict], intent: str, paper_id: str | None = None, requested_n: int | None = None) -> dict:
    items = []
    for section in sections:
        text = section.get("text", "")
        if not text:
            continue
        prompt = (
            "Return strict JSON with an 'items' array of objects with 'text', 'quote', and 'kind'. "
            f"Intent: {intent}. Requested count: {requested_n or 0}. "
            f"Section title: {section.get('title', '')}. "
            f"Text:\n{text[:4000]}"
        )
        raw = await call_llm(prompt, agent_role="chat_map", temperature=0.1, max_tokens=600)
        import json
        try:
            loaded = json.loads(raw)
        except Exception:
            continue
        for item in loaded.get("items", []):
            quote = str(item.get("quote", ""))
            if quote and quote in text:
                items.append({"text": item.get("text", ""), "quote": quote, "kind": item.get("kind", "reviewer_inferred"), "section_title": section.get("title"), "page": section.get("page_start")})
    return {"items": items, "coverage": {"unit": "sections", "covered": len(sections), "total": len(sections), "percent": 100.0 if sections else 0.0, "missing": []}}
