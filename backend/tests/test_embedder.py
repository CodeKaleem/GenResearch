"""Embedding URL, client reuse, and optional-prefix tests."""
import asyncio

from config import settings
from services import embedder


def test_embedder_reuses_client_strips_v1_and_applies_opt_in_prefixes(monkeypatch):
    requests = []
    clients_created = []

    class FakeClient:
        is_closed = False

        def __init__(self, *args, **kwargs):
            clients_created.append(self)

        async def post(self, url, *, json):
            requests.append((url, json["prompt"]))
            return FakeResponse()

        async def aclose(self):
            self.is_closed = True

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embedding": [1.0, 0.0]}

    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.local:11434/v1")
    monkeypatch.setattr(settings, "OLLAMA_EMBED_PREFIXES", True)
    monkeypatch.setattr(embedder.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(embedder, "_client", None)

    async def run_calls():
        documents = await embedder.embed_texts(["paper text"])
        query = await embedder.embed_single("search text")
        await embedder.close_embedder_client()
        return documents, query

    documents, query = asyncio.run(run_calls())

    assert documents == [[1.0, 0.0]]
    assert query == [1.0, 0.0]
    assert len(clients_created) == 1
    assert requests == [
        ("http://ollama.local:11434/api/embeddings", "search_document: paper text"),
        ("http://ollama.local:11434/api/embeddings", "search_query: search text"),
    ]