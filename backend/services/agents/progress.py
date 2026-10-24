"""Real-time progress reporting helper for pipeline nodes."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_queues: dict[str, asyncio.Queue] = {}


def get_session_queue(session_id: str) -> asyncio.Queue:
    if session_id not in _queues:
        _queues[session_id] = asyncio.Queue()
    return _queues[session_id]


def remove_session_queue(session_id: str) -> None:
    _queues.pop(session_id, None)


def emit_progress(session_id: str | None, node: str, log: str, status: str = "running") -> None:
    """Emit an immediate progress event to the active SSE stream."""
    if not session_id or session_id not in _queues:
        return
    try:
        _queues[session_id].put_nowait({
            "type": "state_update",
            "node": node,
            "state": {
                "current_step": node,
                "steps_log": [log],
                "status": status,
            },
        })
    except Exception as exc:
        logger.debug(f"Failed to emit progress for {session_id}: {exc}")
