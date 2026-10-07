# ============================================================
# GenResearch — Chat Router
# RAG-based Q&A: Ask questions about uploaded documents
# ============================================================
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from services.doc_chat.handlers.citations import handle_citations
from services.doc_chat.handlers.items_list import handle_items_list
from services.doc_chat.handlers.qa import handle_qa, handle_qa_stream
from services.doc_chat.handlers.sections_list import handle_sections_list
from services.doc_chat.intent import route_query
from services.rag_service import generate_answer, generate_answer_stream, semantic_search

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Request / Response Models ─────────────────────────────────
class AskRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = 5
    paper_id: str | None = None  # optional: scope to a specific paper


class SourceRef(BaseModel):
    paper_id: str
    title: str
    relevance: float
    section_title: str | None = None
    page: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    chunks_used: int
    model: str
    intent: str | None = None
    coverage: dict | None = None
    items: list[dict] | None = None


class SearchRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = 5
    paper_id: str | None = None


# ── POST /chat/ask ────────────────────────────────────────────
@router.post("/ask", response_model=AskResponse, response_model_exclude_none=True)
async def ask_question(req: AskRequest):
    """
    Ask a question about your uploaded documents.
    Uses semantic search (nomic-embed-text) to find relevant chunks,
    then generates an answer using the configured local chat model.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required.")

    try:
        if settings.CHAT_INTENT_ROUTING:
            intent, requested_n = route_query(req.query)
            if intent == "citations":
                result = await handle_citations(user_id=req.user_id, query=req.query, paper_id=req.paper_id, top_k=req.top_k)
            elif intent == "sections_list":
                result = await handle_sections_list(user_id=req.user_id, paper_id=req.paper_id)
            elif intent == "items_list":
                result = await handle_items_list(user_id=req.user_id, paper_id=req.paper_id)
            elif intent == "qa":
                result = await generate_answer(
                    user_id=req.user_id,
                    query=req.query,
                    top_k=req.top_k,
                    paper_id=req.paper_id,
                    exclude_references=True,
                )
            else:
                result = await generate_answer(
                    user_id=req.user_id,
                    query=req.query,
                    top_k=req.top_k,
                    paper_id=req.paper_id,
                    exclude_references=True,
                )
            if intent != "qa":
                result["intent"] = intent
            return AskResponse(**result)

        result = await generate_answer(
            user_id=req.user_id,
            query=req.query,
            top_k=req.top_k,
            paper_id=req.paper_id,
        )
        return AskResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {e}")


# ── POST /chat/ask-stream ────────────────────────────────────
@router.post("/ask-stream")
async def ask_question_stream(req: AskRequest):
    """
    Streaming version: returns tokens as newline-delimited JSON (NDJSON).
    Each line is a JSON object with a "type" field:
      - {"type": "sources", "sources": [...]}
      - {"type": "token", "content": "..."}
      - {"type": "done"}
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required.")

    async def _streaming_handler():
        if settings.CHAT_INTENT_ROUTING:
            intent, _ = route_query(req.query)
            if intent == "citations":
                result = await handle_citations(user_id=req.user_id, query=req.query, paper_id=req.paper_id, top_k=req.top_k)
                yield json.dumps({"type": "sources", "sources": result.get("sources", [])}) + "\n"
                yield json.dumps({"type": "token", "content": result.get("answer", "")}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return
            if intent in {"sections_list", "items_list"}:
                result = await handle_sections_list(user_id=req.user_id, paper_id=req.paper_id) if intent == "sections_list" else await handle_items_list(user_id=req.user_id, paper_id=req.paper_id)
                yield json.dumps({"type": "sources", "sources": result.get("sources", [])}) + "\n"
                yield json.dumps({"type": "token", "content": result.get("answer", "")}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return
        async for item in generate_answer_stream(
            user_id=req.user_id,
            query=req.query,
            top_k=req.top_k,
            paper_id=req.paper_id,
            exclude_references=True if settings.CHAT_INTENT_ROUTING else False,
        ):
            yield item

    return StreamingResponse(_streaming_handler(), media_type="application/x-ndjson")


# ── POST /chat/search ────────────────────────────────────────
@router.post("/search")
async def search_documents(req: SearchRequest):
    """
    Semantic search only (no LLM generation).
    Returns the most relevant document chunks for a query.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        results = await semantic_search(
            user_id=req.user_id,
            query=req.query,
            top_k=req.top_k,
            paper_id=req.paper_id,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
