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
    ("How many citations are there?", "citation_count"),
    ("How many references does this paper have?", "citation_count"),
    ("What is the citation count?", "citation_count"),
    ("Count the references", "citation_count"),
    ("List all the figures", "items_list"),
    ("How many tables are there?", "items_list"),
    ("Extract all references", "citations"),
    ("Which papers are cited?", "citations"),
    ("Show the table of contents", "sections_list"),
    ("Summarize this paper", "summary"),
    ("What are the main conclusions?", "summary"),
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


def test_right_sized_prompt_distinguishes_factual_and_complex_queries():
    chunks = [{"paper_id": "p1", "title": "Paper A", "text": "Content", "page": 1}]
    
    factual_prompt = rag_service._build_rag_prompt("Who wrote this?", chunks)
    assert "CONCISE FACTUAL LOOKUP" in factual_prompt
    assert "Markdown Headings: STRICTLY FORBIDDEN" in factual_prompt
    assert "Concise Grounded Answer:" in factual_prompt
    
    deep_prompt = rag_service._build_rag_prompt("Summarize the methodology and findings", chunks)
    assert "COMPREHENSIVE / ANALYTICAL QUERY" in deep_prompt
    assert "Descriptive Grounded Answer:" in deep_prompt


def test_main_conclusions_prompt_is_structured_and_not_a_factual_lookup():
    chunks = [{"paper_id": "p1", "title": "Paper A", "text": "Content", "page": 1}]
    prompt = rag_service._build_rag_prompt("What are the main conclusions?", chunks, intent="summary")

    assert "COMPREHENSIVE / ANALYTICAL QUERY" in prompt
    assert "supporting takeaways as concise bullets" in prompt


def test_untagged_drafting_monologue_is_removed_from_final_answer():
    raw = (
        "Alright, let me tackle this user query step by step.\n\n"
        "The user wants to know the main conclusions from the provided document excerpts.\n\n"
        "Final version: The paper identifies interpretability as a challenge [Source 1, p. 8]."
    )

    thinking, answer = llm_service.extract_thinking_and_answer(raw)

    assert "step by step" in thinking
    assert answer == "The paper identifies interpretability as a challenge [Source 1, p. 8]."


def test_page1_block_merging_keeps_authors_intact():
    from ingestion.pdf_parser import ParsedBlock
    from ingestion.structured_chunker import _merge_blocks_for_chunking
    
    blocks = [
        ParsedBlock("Adversarial Risk Analysis", page=1, section_heading="Title & Authors"),
        ParsedBlock("David Ríos Insua", page=1, section_heading="Title & Authors"),
        ParsedBlock("Royal Academy of Sciences, Madrid, Spain", page=1, section_heading="Title & Authors"),
        ParsedBlock("Fabrizio Ruggeri", page=1, section_heading="Title & Authors"),
    ]
    merged = _merge_blocks_for_chunking(blocks, max_merge_len=1000)
    assert len(merged) == 1
    assert "David Ríos Insua" in merged[0].text
    assert "Fabrizio Ruggeri" in merged[0].text
    assert "Adversarial Risk Analysis" in merged[0].text


def test_self_check_catches_missed_author():
    chunks = [
        {
            "paper_id": "p1",
            "title": "Adversarial Risk Analysis",
            "page": 1,
            "text": "Adversarial Risk Analysis\nDavid Ríos Insua, Fabrizio Ruggeri, Michael P. Wiper\nAbstract: We propose...",
            "metadata": {"section_heading": "Title & Authors"},
        }
    ]
    # Incomplete draft that missed David Ríos Insua
    draft = "This paper was written by Fabrizio Ruggeri and Michael P. Wiper."
    verified = rag_service._self_check_factual_answer("Who wrote this?", draft, chunks)
    assert "David Ríos Insua" in verified or "David Rios Insua" in verified
