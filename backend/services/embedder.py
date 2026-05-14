# ============================================================
# GenResearch — Ollama Embedder
# Async embedding via local Ollama nomic-embed-text
# ============================================================
import httpx
from config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Ollama's nomic-embed-text model.
    Returns a list of embedding vectors (one per chunk).
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for text in texts:
            response = await client.post(
                url,
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings.append(data["embedding"])

    return embeddings


async def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    result = await embed_texts([text])
    return result[0]
