from __future__ import annotations

import logging
from typing import Any

from database.supabase_client import get_supabase
from services import request_context

logger = logging.getLogger(__name__)


def _insert(table: str, payload: dict[str, Any]) -> None:
    try:
        get_supabase().table(table).insert(payload).execute()
    except Exception:
        # Tracking is best effort and must never break the research request.
        pass


def create_task(user_id: str, title: str, agent_type: str, paper_count: int = 0) -> str | None:
    if not user_id:
        return None
    try:
        result = get_supabase().table("tasks").insert({
            "user_id": user_id,
            "title": title,
            "agent_type": agent_type,
            "paper_count": paper_count,
            "status": "processing",
        }).execute()
        return result.data[0]["id"] if result.data else None
    except Exception:
        return None


def complete_task(task_id: str | None, status: str, quality_score: int | None = None) -> None:
    if not task_id:
        return
    payload: dict[str, Any] = {"status": status}
    if quality_score is not None:
        payload["quality_score"] = max(0, min(100, int(quality_score)))
    try:
        get_supabase().table("tasks").update(payload).eq("id", task_id).execute()
    except Exception:
        pass


def save_task_result(task_id: str | None, user_id: str, type_: str, content: str, title: str = "", score: int | None = None) -> None:
    if not task_id or not user_id:
        return
    payload: dict[str, Any] = {
        "task_id": task_id,
        "user_id": user_id,
        "type": type_,
        "title": title,
        "content": content,
    }
    if score is not None:
        payload["score"] = max(0, min(100, int(score)))
    _insert("task_results", payload)


def log_agent_event(level: str, message: str, agent: str | None = None, user_id: str | None = None) -> None:
    _insert("agent_logs", {
        "level": level,
        "message": message[:2000],
        "agent": agent,
        "user_id": user_id,
    })


def save_citation_block(user_id: str, title: str, source_text: str, paper_id: str | None = None, authors: str = "", year: str = "", doi: str | None = None) -> None:
    if not user_id:
        return
    _insert("citations", {
        "user_id": user_id,
        "paper_id": paper_id,
        "authors": authors,
        "year": year,
        "title": title,
        "source": source_text[:4000],
        "doi": doi,
    })


def raise_system_alert(title: str, message: str, severity: str = "warning", agent: str | None = None) -> None:
    _insert("system_alerts", {
        "title": title[:200],
        "message": message[:2000],
        "severity": severity,
        "status": "active",
        "agent": agent,
    })


def log_api_cost(agent: str, model: str, tokens_used: int = 0, cost_usd: float = 0.0, user_id: str | None = None) -> None:
    _insert("api_cost_logs", {
        "agent": agent,
        "model": model,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "user_id": user_id,
    })


def save_generated_claim(
    session_id: str,
    section: str,
    claim_text: str,
    cited_chunk_ids: list[str],
    verdict: str,
    discrepancy: str | None = None,
    corrected_text: str | None = None,
) -> None:
    """Persist verification evidence without making generation depend on DB health."""
    if not session_id:
        return
    _insert("generated_claims", {
        "session_id": session_id,
        "section": section,
        "claim_text": claim_text[:10000],
        "cited_chunk_ids": cited_chunk_ids,
        "verdict": verdict,
        "discrepancy": discrepancy,
        "corrected_text": corrected_text,
    })


def log_audit_event(
    node_name: str,
    session_id: str | None = None,
    model_used: str | None = None,
    prompt_hash: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: int = 0,
) -> None:
    _insert("audit_log", {
        "session_id": session_id or request_context.get_session_id(),
        "node_name": node_name,
        "model_used": model_used,
        "prompt_hash": prompt_hash,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
    })