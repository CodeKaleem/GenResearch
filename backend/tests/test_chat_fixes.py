"""Regression tests for the chat speed/reliability fixes."""
import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import settings
from routers import chat as chat_router
from services import llm_service, rag_service
from services.doc_chat.intent import classify_intent, parse_requested_count
from services.llm_models import ModelSpec


# ── intent routing ───────────────────────────────────────────
@pytest.mark.parametrize("query,expected", [
    ("What do the figures show?", "qa"),
    ("Give me the main findings", "qa"),
    ("What does reference [12] say about dropout?", "qa"),
    ("Explain Table 2 results", "qa"),
    ("Which method excited the authors most?", "qa"),
    ("List all the figures", "items_list"),
    ("How many tables are there?", "items_list"),
    ("Extract all references", "citations"),
    ("Which papers are cited?", "citations"),
    ("Show the table of contents", "sections_list"),
    ("Summarize this paper", "summary"),
    ("What are the research gaps?", "gaps"),
    ("What are the main contributions?", "contributions"),
    ("What is future work here?", "future_work"),
    ("How can this paper be improved?", "improvements"),
])
def test_intent_routing_uses_word_boundaries_and_clear_requests(query, expected):
    assert classify_intent(query) == expected


def test_requested_count_ignores_stray_numbers():
    assert parse_requested_count("top 5 research gaps") == 5
    assert parse_requested_count("Explain Table 2 in the 2020 paper") is None
    assert parse_requested_count("") is None


# ── reference filtering ──────────────────────────────────────
def test_reference_heuristic_keeps_body_text_and_drops_bibliography():
    body = "As shown in [1] the method works, in line with Smith, J. (2020)."
    bibliography = "[1] A. Smith, J. Doe. Title. 2020.\n[2] B. Lee, K. Kim. Other. 2021."
    assert rag_service._looks_like_reference_list(body) is False
    assert rag_service._looks_like_reference_list(bibliography) is True


def _make_collection(rows):
    class FakeCollection:
        def __init__(self):
            self.n_results = None

        def count(self):
            return len(rows)

        def query(self, **kwargs):
            self.n_results = kwargs["n_results"]
            chosen = rows[: kwargs["n_results"]]
            return {
                "ids": [[r["id"] for r in chosen]],
                "documents": [[r["text"] for r in chosen]],
                "metadatas": [[{"paper_id": "p1", "title": "T", "page": r["page"]} for r in chosen]],
                "distances": [[r["distance"] for r in chosen]],
            }

    return FakeCollection()


def test_semantic_search_overfetches_and_batches_reference_lookup(monkeypatch):
    rows = [{"id": f"c{i}", "text": f"body {i}", "page": 2 if i < 3 else 20, "distance": 0.1 * (i + 1)} for i in range(9)]
    collection = _make_collection(rows)
    calls = []

    def fake_ref_pages(paper_ids):
        calls.append(list(paper_ids))
        return {"p1": 10}  # pages >= 10 are the bibliography

    async def fake_embed(query):
        return [1.0]

    monkeypatch.setattr(rag_service, "embed_single", fake_embed)
    monkeypatch.setattr(rag_service, "get_user_collection", lambda user_id: collection)
    monkeypatch.setattr(rag_service, "_get_ref_start_pages_sync", fake_ref_pages)
    monkeypatch.setattr(settings, "CHAT_FETCH_MULTIPLIER", 3)

    hits = asyncio.run(rag_service.semantic_search("u", "q", top_k=3, exclude_references=True))

    assert collection.n_results == 9            # over-fetched 3x
    assert [h["id"] for h in hits] == ["c0", "c1", "c2"]
    assert len(calls) == 1                      # one batched lookup, not one per chunk


# ── answer generation ────────────────────────────────────────
def _hit(pid="paper-1", title="Paper One", page=4, distance=0.2, chunk_index=0, text="Evidence text."):
    return {"id": f"{pid}-{chunk_index}", "text": text, "paper_id": pid, "title": title,
            "page": page, "distance": distance, "chunk_index": chunk_index, "metadata": {"section_heading": "Results"}}


def test_irrelevant_chunks_return_not_found_without_calling_the_llm(monkeypatch):
    async def fake_search(*args, **kwargs):
        return [_hit(distance=0.95)]

    async def fail_llm(*args, **kwargs):
        raise AssertionError("LLM must not be called when nothing is relevant")

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    monkeypatch.setattr(rag_service, "call_llm", fail_llm)

    result = asyncio.run(rag_service.generate_answer("u", "unrelated question"))

    assert result["chunks_used"] == 0
    assert result["answer"] == rag_service.NO_RESULTS_MESSAGE


def test_followup_uses_history_for_retrieval_and_prompt_has_page_provenance(monkeypatch):
    seen = {}

    async def fake_search(user_id, query, top_k, *args, **kwargs):
        seen["query"] = query
        seen["top_k"] = top_k
        return [_hit(), _hit(pid="paper-2", title="Paper Two", page=9, chunk_index=1)]

    async def fake_llm(prompt, *, agent_role, temperature, max_tokens):
        seen["prompt"] = prompt
        return "ok"

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    monkeypatch.setattr(rag_service, "call_llm", fake_llm)

    history = [{"role": "user", "content": "What dataset was used?"}, {"role": "assistant", "content": "CIFAR-10 [Source 1]"}]
    result = asyncio.run(rag_service.generate_answer("u", "how accurate was it?", top_k=5, history=history))

    assert seen["query"].startswith("What dataset was used?")
    assert seen["top_k"] >= settings.CHAT_TOP_K
    assert "[Source 1: Paper One | p. 4 | Results]" in seen["prompt"]
    assert "[Source 2: Paper Two | p. 9 | Results]" in seen["prompt"]
    assert "CONVERSATION SO FAR" in seen["prompt"]
    # numbering in the prompt matches the order of the sources sent to the UI
    assert [s["paper_id"] for s in result["sources"]] == ["paper-1", "paper-2"]


def test_broad_intent_spreads_across_pages_and_skips_distance_cutoff(monkeypatch):
    async def fake_search(*args, **kwargs):
        # first four are neighbours on the same page; far chunk on a different page
        return [_hit(page=1, chunk_index=i, distance=0.3) for i in range(4)] + [_hit(page=12, chunk_index=9, distance=0.9)]

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    chunks = asyncio.run(rag_service._prepare_context("u", "Summarize this paper", 5, None, True, None, "summary"))[0]

    pages = [c["page"] for c in chunks]
    assert 12 in pages and 1 in pages            # distant page kept despite distance 0.9
    assert pages == sorted(pages)                # reading order


def test_context_budget_trims_evidence(monkeypatch):
    monkeypatch.setattr(settings, "CHAT_CONTEXT_CHARS", 250)
    chunks = [_hit(chunk_index=i, text="x" * 100, distance=0.1 + i / 100) for i in range(6)]
    assert len(rag_service._select_chunks(chunks, "qa", 8)) == 2


# ── router ───────────────────────────────────────────────────
def test_stream_failure_emits_error_event_instead_of_dropping_connection(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router)
    client = TestClient(app)

    async def boom(*args, **kwargs):
        raise RuntimeError("ollama down")
        yield  # pragma: no cover

    monkeypatch.setattr(chat_router, "generate_answer_stream", boom)
    response = client.post("/chat/ask-stream", json={"user_id": "u", "query": "What did they find?"})
    events = [json.loads(line) for line in response.iter_lines() if line]

    assert [e["type"] for e in events] == ["error", "done"]
    assert "ollama down" in events[0]["message"]


def test_history_is_accepted_and_passed_through(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router)
    client = TestClient(app)
    captured = {}

    async def fake_generate(**kwargs):
        captured.update(kwargs)
        return {"answer": "a", "sources": [], "chunks_used": 0, "model": "m"}

    monkeypatch.setattr(chat_router, "generate_answer", fake_generate)
    response = client.post("/chat/ask", json={
        "user_id": "u", "query": "and the second one?",
        "history": [{"role": "user", "content": "first?"}, {"role": "assistant", "content": "answer"}],
    })

    assert response.status_code == 200
    assert [m.role for m in captured["history"]] == ["user", "assistant"]


# ── llm payload ──────────────────────────────────────────────
def test_payload_has_keep_alive_and_lets_ollama_pick_gpu_when_negative(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_KEEP_ALIVE", "30m")
    spec = ModelSpec("mid", "m", max_concurrent=1, num_thread=4, num_gpu=-1, num_ctx=8192)
    payload = llm_service._request_payload(
        spec, [{"role": "user", "content": "hi"}], stream=True, temperature=0.3, max_tokens=10, context_limit=None
    )
    assert payload["keep_alive"] == "30m"
    assert "num_gpu" not in payload["options"]
    assert payload["options"]["num_thread"] == 4


def test_chat_roles_get_tighter_read_timeout(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_REQUEST_TIMEOUT", 600.0)
    monkeypatch.setattr(settings, "OLLAMA_CHAT_READ_TIMEOUT", 120.0)
    assert llm_service._read_timeout_for_role("chat") == 120.0
    assert llm_service._read_timeout_for_role("draft") is None
