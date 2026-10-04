# ============================================================
# GenResearch — Ollama Embedder
# Async embedding via local Ollama nomic-embed-text
# ============================================================
import asyncio
import httpx
from config import settings
from services.llm_service import _ollama_base_url

_client: httpx.AsyncClient | None = None
_client_timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=30.0)


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=_client_timeout)
    return _client


async def close_embedder_client() -> None:
    """Close the reusable embedding client during application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Ollama's nomic-embed-text model.
    Returns a list of embedding vectors (one per chunk).
    """
    url = f"{_ollama_base_url()}/api/embeddings"
    
    sem = asyncio.Semaphore(5)

    async def fetch_embedding(client, text):
        async with sem:
            response = await client.post(
                url,
                json={
                    "model": settings.OLLAMA_EMBED_MODEL,
                    "prompt": (
                        f"search_document: {text}"
                        if settings.OLLAMA_EMBED_PREFIXES
                        else text
                    ),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    client = _get_client()
    tasks = [fetch_embedding(client, text) for text in texts]
    embeddings = await asyncio.gather(*tasks)

    return list(embeddings)


async def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    if settings.OLLAMA_EMBED_PREFIXES:
        result = await _embed_texts_with_prefix([text], "search_query: ")
    else:
        result = await embed_texts([text])
    return result[0]


async def _embed_texts_with_prefix(texts: list[str], prefix: str) -> list[list[float]]:
    original_setting = settings.OLLAMA_EMBED_PREFIXES
    prefixed = [f"{prefix}{text}" for text in texts]
    url = f"{_ollama_base_url()}/api/embeddings"
    client = _get_client()
    semaphore = asyncio.Semaphore(5)

    async def fetch_embedding(text: str) -> list[float]:
        async with semaphore:
            response = await client.post(
                url,
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            )
            response.raise_for_status()
            return response.json()["embedding"]

    if not original_setting:
        return await embed_texts(texts)
    return list(await asyncio.gather(*(fetch_embedding(text) for text in prefixed)))
