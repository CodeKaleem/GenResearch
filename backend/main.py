# ============================================================
# GenResearch — FastAPI Application Entry Point
# Vector Database Pipeline for Research Paper Management
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers.papers import router as papers_router
from routers.chat import router as chat_router
from routers.pipeline import router as pipeline_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Vector database pipeline with RAG: Upload PDFs → Extract → Chunk → Embed → Store → Ask Questions",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(papers_router)
app.include_router(chat_router)
app.include_router(pipeline_router)


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
