"""Regression coverage for duplicate pipeline stream requests."""
import asyncio
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from config import Settings
from routers import pipeline as pipeline_router


def test_active_session_stream_returns_conflict_and_releases_lock(monkeypatch):
    session_id = "concurrent-session"
    lock = asyncio.Lock()

    class FakeGraph:
        def get_state(self, config):
            return SimpleNamespace(values={}, next=())

        async def astream(self, *args, **kwargs):
            yield {"topic_input": {"current_step": "topic_input", "steps_log": []}}

    monkeypatch.setattr(pipeline_router, "_pipeline_graph", FakeGraph())
    monkeypatch.setattr(pipeline_router, "_sessions", {
        session_id: {
            "state": {"user_id": "user-1", "topic": "Concurrency"},
            "config": {"configurable": {"thread_id": session_id}},
            "task_id": None,
            "stream_lock": lock,
        }
    })
    monkeypatch.setattr(pipeline_router.tracking, "log_agent_event", lambda *args, **kwargs: None)

    async def run():
        first = await pipeline_router.stream_pipeline(session_id)
        assert lock.locked()
        with pytest.raises(HTTPException) as error:
            await pipeline_router.stream_pipeline(session_id)
        assert error.value.status_code == 409
        chunks = [chunk async for chunk in first.body_iterator]
        assert any('"type": "done"' in (chunk.decode() if isinstance(chunk, bytes) else chunk) for chunk in chunks)
        assert not lock.locked()

    asyncio.run(run())


def test_debug_defaults_to_false():
    assert 'DEBUG: bool = os.getenv("DEBUG", "False")' in inspect.getsource(Settings)