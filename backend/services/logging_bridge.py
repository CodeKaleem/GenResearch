from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from services import request_context, tracking

# WARNING+ records are written to Supabase. Doing that inline blocked whichever
# coroutine happened to log (e.g. every LLM fallback warning). Use one background thread.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="supabase-log")

_LEVEL_MAP = {
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}


class SupabaseLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level = _LEVEL_MAP.get(record.levelno)
        if not level or record.name == "services.tracking":
            return
        try:
            _executor.submit(
                tracking.log_agent_event,
                level=level,
                message=record.getMessage(),
                agent=record.name,
                user_id=request_context.get_user_id(),
            )
        except Exception:
            pass


_installed = False


def install_supabase_log_handler() -> None:
    global _installed
    if _installed:
        return
    logging.getLogger("services").addHandler(SupabaseLogHandler(level=logging.WARNING))
    _installed = True