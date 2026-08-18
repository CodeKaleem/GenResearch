# ============================================================
# GenResearch — Chat Router
# RAG-based Q&A: Ask questions about uploaded documents
# ============================================================
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    chunks_used: int
    model: str


class SearchRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = 5
    paper_id: str | None = None


# ── POST /chat/ask ────────────────────────────────────────────
@router.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """
    Ask a question about your uploaded documents.
    Uses semantic search (nomic-embed-text) to find relevant chunks,
    then generates an answer using Mistral 7B.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required.")

    try:
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

    return StreamingResponse(
        generate_answer_stream(
            user_id=req.user_id,
            query=req.query,
            top_k=req.top_k,
            paper_id=req.paper_id,
        ),
        media_type="application/x-ndjson",
    )


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
