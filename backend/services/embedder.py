# ============================================================
# GenResearch — Ollama Embedder
# Async embedding via local Ollama nomic-embed-text
# ============================================================
import httpx
import asyncio
from config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Ollama's nomic-embed-text model.
    Returns a list of embedding vectors (one per chunk).
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    
    sem = asyncio.Semaphore(5)

    async def fetch_embedding(client, text):
        async with sem:
            response = await client.post(
                url,
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async with httpx.AsyncClient(timeout=120.0) as client:
        tasks = [fetch_embedding(client, text) for text in texts]
        embeddings = await asyncio.gather(*tasks)

    return list(embeddings)


async def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    result = await embed_texts([text])
    return result[0]
