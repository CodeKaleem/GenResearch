"""Protocol regressions for the shared Ollama LLM client."""
import asyncio

import httpx

from config import settings
from services import llm_service
from services.llm_models import ModelSpec


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_call_llm_uses_native_api_options_and_strips_thinking(monkeypatch):
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, json, **kwargs):
            requests.append((url, json))
            return FakeResponse({
                "message": {"content": "Visible <think>private reasoning</think> answer"},
                "prompt_eval_count": 12,
                "eval_count": 4,
            })

    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.local:11434/v1")
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(llm_service, "_semaphore", lambda spec: asyncio.Semaphore(1))

    spec = ModelSpec(
        "heavy",
        "qwen3:8b",
        max_concurrent=1,
        num_thread=5,
        num_gpu=0,
        num_ctx=6000,
        think=False,
    )
    result, usage = asyncio.run(
        llm_service._call_ollama_once(
            spec,
            [{"role": "user", "content": "prompt"}],
            temperature=0.25,
            max_tokens=77,
            context_limit=1234,
        )
    )

    url, payload = requests[0]
    assert url == "http://ollama.local:11434/api/chat"
    assert payload["options"] == {
        "temperature": 0.25,
        "num_predict": 77,
        "num_ctx": 1234,
        "num_thread": spec.num_thread,
        "num_gpu": spec.num_gpu,
    }
    assert payload["think"] is False
    assert result == "Visible  answer"
    assert usage == {"prompt_eval_count": 12, "eval_count": 4}


def test_timeout_falls_back_without_retrying_same_tier(monkeypatch):
    requests = []
    specs = [
        ModelSpec("primary", "primary-model", max_concurrent=1, num_thread=1),
        ModelSpec("fallback", "fallback-model", max_concurrent=1, num_thread=1),
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, json, **kwargs):
            requests.append(json["model"])
            if json["model"] == "primary-model":
                raise httpx.ReadTimeout("slow model")
            return FakeResponse({"message": {"content": "fallback answer"}})

    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.local:11434")
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(llm_service, "get_chain_for_role", lambda role: specs)
    monkeypatch.setattr(llm_service, "_semaphore", lambda spec: asyncio.Semaphore(1))
    monkeypatch.setattr(llm_service.tracking, "log_api_cost", lambda **kwargs: None)
    monkeypatch.setattr(llm_service.tracking, "log_audit_event", lambda **kwargs: None)

    answer = asyncio.run(llm_service.call_llm("prompt", agent_role="test"))

    assert answer == "fallback answer"
    assert requests == ["primary-model", "fallback-model"]


def test_call_llm_stream_parses_native_ndjson_and_strips_think(monkeypatch):
    specs = [ModelSpec("only", "native-model", max_concurrent=1, num_thread=1)]

    class FakeResponse:
        def __init__(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield '{"message":{"content":"before<think>private"},"done":false}'
            yield '{"message":{"content":" thoughts</think>after"},"done":false}'
            yield '{"message":{"content":""},"done":true}'

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def stream(self, method, url, *, json, **kwargs):
            assert url == "http://ollama.local:11434/api/chat"
            assert json["stream"] is True
            return FakeResponse()

    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.local:11434")
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(llm_service, "get_chain_for_role", lambda role: specs)
    monkeypatch.setattr(llm_service, "_semaphore", lambda spec: asyncio.Semaphore(1))

    async def collect():
        return [token async for token in llm_service.call_llm_stream("prompt", agent_role="test")]

    assert asyncio.run(collect()) == ["before", "after"]