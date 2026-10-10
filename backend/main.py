# ============================================================
# GenResearch — FastAPI Application Entry Point
# Vector Database Pipeline for Research Paper Management
# ============================================================
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers.papers import router as papers_router
from routers.chat import router as chat_router
from routers.doc_structure import router as doc_structure_router
from routers.pipeline import router as pipeline_router
from routers.reports import router as reports_router
from routers.agent_tasks import router as agent_tasks_router
from routers.research_search import router as research_search_router
from services.logging_bridge import install_supabase_log_handler

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Vector database pipeline with RAG: Upload PDFs → Extract → Chunk → Embed → Store → Ask Questions",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):(3000|3001)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

# ── Routers ───────────────────────────────────────────────────
app.include_router(papers_router)
app.include_router(chat_router)
app.include_router(doc_structure_router)
app.include_router(pipeline_router)
app.include_router(reports_router)
app.include_router(agent_tasks_router)
app.include_router(research_search_router)

install_supabase_log_handler()


# ── Health Check ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
