"""Chat API contract and safe streaming fallback regressions."""
import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import settings
from routers import chat as chat_router
from services import llm_service, rag_service
from services.llm_models import ModelSpec


@pytest.fixture
def chat_client():
    app = FastAPI()
    app.include_router(chat_router.router)
    return TestClient(app)


def _hit():
    return {
        "id": "chunk-1",
        "text": "A controlled study evaluated this approach.",
        "paper_id": "paper-1",
        "title": "A controlled study",
        "distance": 0.2,
    }


def test_chat_ask_uses_llm_service_and_keeps_response_contract(monkeypatch, chat_client):
    async def fake_search(*args, **kwargs):
        return [_hit()]

    async def fake_call_llm(prompt, *, agent_role, temperature, max_tokens):
        assert agent_role == "chat"
        assert temperature == 0.3
        assert max_tokens == 4096
        return "The study supports the approach."

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    monkeypatch.setattr(rag_service, "call_llm", fake_call_llm, raising=False)

    response = chat_client.post(
        "/chat/ask",
        json={"user_id": "user-1", "query": "What did the study show?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "answer": "The study supports the approach.",
        "sources": [{"paper_id": "paper-1", "title": "A controlled study", "relevance": 0.8}],
        "chunks_used": 1,
        "model": settings.OLLAMA_MID_MODEL,
    }


def test_chat_stream_emits_sources_tokens_and_done(monkeypatch, chat_client):
    async def fake_search(*args, **kwargs):
        return [_hit()]

    async def fake_stream(prompt, *, agent_role, temperature, max_tokens):
        assert agent_role == "chat"
        assert temperature == 0.3
        assert max_tokens == 4096
        yield "The study "
        yield "supports the approach."

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    monkeypatch.setattr(rag_service, "call_llm_stream", fake_stream, raising=False)

    response = chat_client.post(
        "/chat/ask-stream",
        json={"user_id": "user-1", "query": "What did the study show?"},
    )
    events = [json.loads(line) for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert [event["type"] for event in events] == ["sources", "token", "token", "done"]
    assert events[0]["sources"][0]["paper_id"] == "paper-1"


def test_chat_stream_without_sources_still_uses_sources_token_done(monkeypatch, chat_client):
    async def fake_search(*args, **kwargs):
        return []

    monkeypatch.setattr(rag_service, "semantic_search", fake_search)
    response = chat_client.post(
        "/chat/ask-stream",
        json={"user_id": "user-1", "query": "Question without documents"},
    )
    events = [json.loads(line) for line in response.iter_lines() if line]

    assert [event["type"] for event in events] == ["sources", "token", "done"]
    assert events[0]["sources"] == []


def test_llm_stream_does_not_fallback_after_partial_output(monkeypatch):
    models = [
        ModelSpec("mid", "mid-model", max_concurrent=1, num_thread=1),
        ModelSpec("light", "light-model", max_concurrent=1, num_thread=1),
    ]
    monkeypatch.setattr(llm_service, "get_chain_for_role", lambda _: models)
    monkeypatch.setattr(llm_service, "_semaphore", lambda spec: asyncio.Semaphore(1))
    requested_models = []

    class FakeResponse:
        def __init__(self, model):
            self.model = model

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield '{"message":{"content":"partial"},"done":false}'
            raise RuntimeError("stream interrupted")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, method, url, *, json, **kwargs):
            requested_models.append(json["model"])
            return FakeResponse(json["model"])

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", FakeClient)

    async def consume():
        tokens = []
        with pytest.raises(RuntimeError, match="stream interrupted"):
            async for token in llm_service.call_llm_stream("prompt", agent_role="chat"):
                tokens.append(token)
        return tokens

    assert asyncio.run(consume()) == ["partial"]
    assert requested_models == ["mid-model"]


def test_extract_thinking_and_answer_tagged():
    raw = "<think>Let me analyze the documents. The study mentions meta-analysis.</think> The methodology used was meta-analysis."
    thinking, answer = llm_service.extract_thinking_and_answer(raw)
    assert "Let me analyze the documents" in thinking
    assert answer == "The methodology used was meta-analysis."


def test_extract_thinking_and_answer_untagged_monologue():
    raw = (
        "We are given a user question: 'What methodology was used?' and we have to answer based strictly on the provided document excerpts. "
        "First, I need to scan the document excerpts to see if they mention any specific methodology used in the research.\n\n"
        "Based on the excerpts, the methodology was meta-analysis."
    )
    thinking, answer = llm_service.extract_thinking_and_answer(raw)
    assert "We are given a user question" in thinking
    assert "First, I need to scan" in thinking
    assert answer == "Based on the excerpts, the methodology was meta-analysis."


def test_llm_stream_filters_thinking_events(monkeypatch):
    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            lines = [
                '{"message":{"content":"<think>Considering the question..."},"done":false}',
                '{"message":{"content":" Done thinking.</think>The answer is 42."},"done":true}',
            ]
            for line in lines:
                yield line

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, method, url, *, json, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", FakeClient)

    async def run():
        events = []
        async for event in llm_service.call_llm_stream("test", agent_role="chat", emit_events=True):
            events.append(event)
        return events

    events = asyncio.run(run())
    assert any(evt[0] == "thinking" for evt in events)
    assert any(evt[0] == "token" and "The answer is 42." in evt[1] for evt in events)


def test_llm_stream_never_emits_think_block_as_answer():
    state = {}
    events = llm_service._filter_stream_events("<think>private reasoning", state)
    assert not any(event_type == "token" for event_type, _ in events)

    events.extend(llm_service._filter_stream_events("</think>Grounded answer.", state))
    answer = "".join(text for event_type, text in events if event_type == "token")
    thinking = "".join(text for event_type, text in events if event_type == "thinking")

    assert thinking == "private reasoning"
    assert answer == "Grounded answer."


def test_llm_stream_filters_chunked_untagged_preamble_and_keeps_final_answer():
    state = {}
    chunks = [
        "Alri",
        "ght, let me tackle this user query step by step.\n\n"
        "I should review the excerpts first.\n\nFinal ver",
        "sion: **Main conclusion**\n- The paper identifies interpretability as a challenge [Source 1].",
    ]
    events = [
        event
        for chunk in chunks
        for event in llm_service._filter_stream_events(chunk, state)
    ]
    events.extend(llm_service._filter_stream_events("", state, final=True))

    answer = "".join(text for event_type, text in events if event_type == "token")
    thinking = "".join(text for event_type, text in events if event_type == "thinking")
    assert "Alright" in thinking
    assert answer == "**Main conclusion**\n- The paper identifies interpretability as a challenge [Source 1]."