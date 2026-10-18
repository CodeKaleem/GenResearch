from __future__ import annotations

import asyncio
import json
import logging
import hashlib
import re
import time
from typing import AsyncIterator

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from services.llm_models import ModelSpec, get_chain_for_role
from services import request_context, tracking

logger = logging.getLogger(__name__)


class NonRetryableLLMError(Exception):
    """Raised when retrying the same local tier will not help."""


_semaphores: dict[str, asyncio.Semaphore] = {}


def _ollama_base_url() -> str:
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    return base_url[:-3] if base_url.endswith("/v1") else base_url


def _native_chat_url() -> str:
    return f"{_ollama_base_url()}/api/chat"


def _request_timeout(read: float | None = None) -> httpx.Timeout:
    return httpx.Timeout(
        connect=10.0,
        read=read if read is not None else settings.OLLAMA_REQUEST_TIMEOUT,
        write=30.0,
        pool=30.0,
    )


def _read_timeout_for_role(agent_role: str) -> float | None:
    """Interactive chat gets a tighter read timeout so fallback happens in minutes, not 10 min."""
    if agent_role.startswith("chat") and agent_role != "chat_map":
        return min(settings.OLLAMA_CHAT_READ_TIMEOUT, settings.OLLAMA_REQUEST_TIMEOUT)
    return None


def _request_payload(
    spec: ModelSpec,
    messages: list[dict],
    *,
    stream: bool,
    temperature: float,
    max_tokens: int,
    context_limit: int | None,
) -> dict:
    options = {
        "temperature": temperature,
        "num_predict": max_tokens,
        "num_ctx": context_limit or spec.num_ctx,
    }
    # A negative value means "let Ollama decide" (use the GPU when there is one).
    # Hard-coding num_gpu=0 forces CPU inference even on a GPU host.
    if spec.num_thread > 0:
        options["num_thread"] = spec.num_thread
    if spec.num_gpu >= 0:
        options["num_gpu"] = spec.num_gpu
    payload = {
        "model": spec.model_id,
        "messages": messages,
        "stream": stream,
        "options": options,
    }
    if settings.OLLAMA_KEEP_ALIVE:
        payload["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
    if spec.think is not None:
        payload["think"] = spec.think
    return payload


_THINK_OPEN_TAGS = ["<think>", "<thought>", "<thinking>"]
_THINK_CLOSE_TAGS = ["</think>", "</thought>", "</thinking>"]


def extract_thinking_and_answer(text: str) -> tuple[str, str]:
    """Separate internal thinking monologue from the user-facing answer.

    Handles both explicit <think>...</think> tags and untagged reasoning preambles
    (e.g., 'We are given a user question: ...' followed by 'Grounded Answer:').
    Returns (thinking, answer).
    """
    if not text:
        return "", ""
    raw = text.strip()
    thinking_parts: list[str] = []

    # 1. Extract tagged <think> blocks
    for m in re.finditer(
        r"<(?:think|thought|thinking)>([\s\S]*?)(?:</(?:think|thought|thinking)>|$)",
        raw,
        re.IGNORECASE,
    ):
        if m.group(1).strip():
            thinking_parts.append(m.group(1).strip())

    cleaned = re.sub(
        r"<(?:think|thought|thinking)>.*?(?:</(?:think|thought|thinking)>|$)",
        "",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    cleaned = re.sub(r"</(?:think|thought|thinking)>", "", cleaned, flags=re.IGNORECASE).strip()

    # 2. Extract untagged reasoning preamble if answer marker is present
    marker_match = re.search(
        r"(?:^|\n+)(?:(?:Concise|Descriptive)\s+Grounded\s+Answer:|(?:\*\*|\#\#)?\s*Answer:?)\s*",
        cleaned,
        flags=re.IGNORECASE,
    )
    if marker_match and marker_match.start() > 0:
        preamble = cleaned[:marker_match.start()].strip()
        if preamble:
            thinking_parts.append(preamble)
        cleaned = cleaned[marker_match.end():].strip()
    else:
        # 3. Check for obvious reasoning preamble at the start
        preamble_match = re.match(
            r"^(?:We are given a user question|First,? I need to|Looking at the document excerpts|Let me check the document|Let's analyze the question|The user is asking)[\s\S]*?\n\n",
            cleaned,
            flags=re.IGNORECASE,
        )
        if preamble_match:
            thinking_parts.append(preamble_match.group(0).strip())
            cleaned = cleaned[preamble_match.end():].strip()

    thinking = "\n\n".join(thinking_parts).strip()
    return thinking, cleaned


def _strip_think_blocks(text: str) -> str:
    return extract_thinking_and_answer(text)[1]


def _partial_tag_suffix_length(text: str, tag: str) -> int:
    lowered = text.lower()
    for length in range(min(len(text), len(tag) - 1), 0, -1):
        if lowered.endswith(tag[:length].lower()):
            return length
    return 0


def _filter_stream_events(content: str, state: dict, *, final: bool = False) -> list[tuple[str, str]]:
    """Stream event splitter that yields ('thinking', chunk) and ('token', chunk)."""
    data = state.get("pending", "") + content
    events: list[tuple[str, str]] = []

    while data:
        lowered = data.lower()

        # 1. Inside explicit <think> block
        if state.get("inside_think", False):
            earliest_close = -1
            close_tag_len = 0
            for tag in _THINK_CLOSE_TAGS:
                pos = lowered.find(tag)
                if pos >= 0 and (earliest_close < 0 or pos < earliest_close):
                    earliest_close = pos
                    close_tag_len = len(tag)

            if earliest_close < 0:
                if final:
                    if data:
                        events.append(("thinking", data))
                    state["pending"] = ""
                    return events
                suffix_length = max((_partial_tag_suffix_length(data, tag) for tag in _THINK_CLOSE_TAGS), default=0)
                emit_len = len(data) - suffix_length
                if emit_len > 0:
                    events.append(("thinking", data[:emit_len]))
                    data = data[emit_len:]
                state["pending"] = data
                return events

            think_text = data[:earliest_close]
            if think_text:
                events.append(("thinking", think_text))
            data = data[earliest_close + close_tag_len:]
            state["inside_think"] = False
            continue

        # 2. Check for start of <think> block
        earliest_open = -1
        open_tag_len = 0
        for tag in _THINK_OPEN_TAGS:
            pos = lowered.find(tag)
            if pos >= 0 and (earliest_open < 0 or pos < earliest_open):
                earliest_open = pos
                open_tag_len = len(tag)

        if earliest_open >= 0:
            before_think = data[:earliest_open]
            if before_think:
                events.append(("token", before_think))
            data = data[earliest_open + open_tag_len:]
            state["inside_think"] = True
            continue

        # 3. Detect untagged reasoning preamble at the start of response
        if state.get("in_preamble", None) is None:
            stripped = data.strip().lower()
            if any(stripped.startswith(p) for p in (
                "we are given a user question",
                "first, i need to",
                "first i need to",
                "looking at the document excerpts",
                "let me check the document",
                "let's analyze the question",
                "the user is asking",
            )):
                state["in_preamble"] = True
            else:
                state["in_preamble"] = False

        if state.get("in_preamble", False):
            marker_match = re.search(
                r"(?:(?:Concise|Descriptive)\s+Grounded\s+Answer:|(?:\*\*|\#\#)?\s*Answer:?)\s*",
                data,
                flags=re.IGNORECASE,
            )
            if marker_match:
                preamble_text = data[:marker_match.start()]
                if preamble_text:
                    events.append(("thinking", preamble_text))
                data = data[marker_match.end():]
                state["in_preamble"] = False
                continue
            else:
                if final:
                    events.append(("thinking", data))
                    state["pending"] = ""
                    return events
                suffix_length = max((_partial_tag_suffix_length(data, m) for m in (
                    "concise grounded answer:", "descriptive grounded answer:", "answer:"
                )), default=0)
                emit_len = len(data) - suffix_length
                if emit_len > 0:
                    events.append(("thinking", data[:emit_len]))
                    data = data[emit_len:]
                state["pending"] = data
                return events

        # 4. Normal user-facing answer token
        if final:
            if data:
                events.append(("token", data))
            state["pending"] = ""
            break

        suffix_length = max((_partial_tag_suffix_length(data, tag) for tag in _THINK_OPEN_TAGS), default=0)
        safe_length = len(data) - suffix_length
        if safe_length > 0:
            events.append(("token", data[:safe_length]))
            data = data[safe_length:]
        state["pending"] = data
        break

    return events


def _filter_think_chunk(content: str, state: dict, *, final: bool = False) -> str:
    events = _filter_stream_events(content, state, final=final)
    return "".join(text for ev_type, text in events if ev_type == "token")


def _semaphore(spec: ModelSpec) -> asyncio.Semaphore:
    if spec.key not in _semaphores:
        _semaphores[spec.key] = asyncio.Semaphore(spec.max_concurrent)
    return _semaphores[spec.key]


def _is_retryable(error: BaseException) -> bool:
    status = getattr(getattr(error, "response", None), "status_code", None)
    return isinstance(status, int) and 500 <= status < 600


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _call_ollama_once(
    spec: ModelSpec,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    context_limit: int | None = None,
    read_timeout: float | None = None,
) -> tuple[str, dict]:
    payload = {
        **_request_payload(
            spec,
            messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            context_limit=context_limit,
        )
    }

    async with _semaphore(spec):
        try:
            async with httpx.AsyncClient(timeout=_request_timeout(read_timeout)) as client:
                response = await client.post(
                    _native_chat_url(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                usage = {
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                }
                return _strip_think_blocks(content), usage
        except httpx.ConnectError as error:
            raise NonRetryableLLMError(
                f"Cannot reach Ollama at {settings.OLLAMA_BASE_URL} for "
                f"{spec.model_id}. Is `ollama serve` running?"
            ) from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise NonRetryableLLMError(
                    f"Model '{spec.model_id}' is not pulled locally. "
                    f"Run: ollama pull {spec.model_id}"
                ) from error
            raise


_background_tasks: set[asyncio.Task] = set()


def _write_tracking(agent_role: str, model_id: str, prompt: str, usage: dict, latency_ms: int, user_id) -> None:
    """Synchronous Supabase inserts; always run off the event loop."""
    tokens_in = int(usage.get("prompt_eval_count") or 0)
    tokens_out = int(usage.get("eval_count") or 0)
    tracking.log_api_cost(
        agent=agent_role,
        model=model_id,
        tokens_used=tokens_in + tokens_out,
        user_id=user_id,
    )
    tracking.log_audit_event(
        node_name=agent_role,
        model_used=model_id,
        prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
    )


def _track_in_background(**kwargs) -> None:
    """Fire-and-forget tracking so remote Supabase writes never delay or block an answer."""
    try:
        task = asyncio.get_running_loop().create_task(asyncio.to_thread(_write_tracking, **kwargs))
    except RuntimeError:
        return
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def call_llm(
    prompt: str,
    *,
    agent_role: str,
    system: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    context_limit: int | None = None,
) -> str:
    chain = get_chain_for_role(agent_role)
    messages = (
        ([{"role": "system", "content": system}] if system else [])
        + [{"role": "user", "content": prompt}]
    )

    last_error: BaseException | None = None
    started_at = time.perf_counter()
    for index, spec in enumerate(chain):
        estimate = (len(prompt) + len(system)) / 3.5
        effective_context = context_limit or spec.num_ctx
        if estimate + max_tokens > effective_context:
            logger.warning(
                "llm_prompt_may_exceed_context",
                extra={
                    "agent_role": agent_role,
                    "tier": spec.key,
                    "estimated_prompt_tokens": round(estimate),
                    "max_tokens": max_tokens,
                    "context_limit": effective_context,
                },
            )
        try:
            logger.info(
                "llm_request",
                extra={
                    "agent_role": agent_role,
                    "tier": spec.key,
                    "attempt_index": index,
                },
            )
            read_timeout = _read_timeout_for_role(agent_role)
            extra = {"read_timeout": read_timeout} if read_timeout is not None else {}
            result, usage = await _call_ollama_once(spec, messages, temperature, max_tokens, context_limit, **extra)
            logger.info(
                "llm_response",
                extra={
                    "agent_role": agent_role,
                    "tier": spec.key,
                    "response_length": len(result),
                },
            )
            _track_in_background(
                agent_role=agent_role,
                model_id=spec.model_id,
                prompt=prompt,
                usage=usage,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                user_id=request_context.get_user_id(),
            )
            return result
        except (NonRetryableLLMError, RetryError) as error:
            logger.warning(
                "llm_tier_failed_falling_back",
                extra={"agent_role": agent_role, "tier": spec.key, "error": str(error)},
            )
            last_error = error
        except Exception as error:
            logger.warning(
                "llm_tier_failed_falling_back",
                extra={
                    "agent_role": agent_role,
                    "tier": spec.key,
                    "fallback_reason": f"{type(error).__name__}: {error}",
                },
            )
            last_error = error

    raise RuntimeError(
        f"All local tiers failed for role '{agent_role}'. "
        f"Chain tried: {[spec.key for spec in chain]}. Last error: {last_error}"
    ) from last_error


async def call_llm_stream(
    prompt: str,
    *,
    agent_role: str,
    system: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    context_limit: int | None = None,
    emit_events: bool = False,
) -> AsyncIterator[any]:
    chain = get_chain_for_role(agent_role)
    messages = (
        ([{"role": "system", "content": system}] if system else [])
        + [{"role": "user", "content": prompt}]
    )

    last_error: BaseException | None = None
    yielded_content = False
    for spec in chain:
        payload = _request_payload(
            spec,
            messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            context_limit=context_limit,
        )
        think_state: dict = {}
        try:
            async with _semaphore(spec):
                async with httpx.AsyncClient(timeout=_request_timeout(_read_timeout_for_role(agent_role))) as client:
                    async with client.stream(
                        "POST",
                        _native_chat_url(),
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            chunk = json.loads(line)
                            msg_obj = chunk.get("message", {})
                            native_thinking = msg_obj.get("thinking", "")
                            if native_thinking:
                                yielded_content = True
                                if emit_events:
                                    yield ("thinking", native_thinking)

                            content = msg_obj.get("content", "")
                            if content:
                                events = _filter_stream_events(content, think_state)
                                for ev_type, text in events:
                                    if text:
                                        yielded_content = True
                                        if emit_events:
                                            yield (ev_type, text)
                                        elif ev_type == "token":
                                            yield text
                            if chunk.get("done"):
                                break
                        remaining_events = _filter_stream_events("", think_state, final=True)
                        for ev_type, text in remaining_events:
                            if text:
                                yielded_content = True
                                if emit_events:
                                    yield (ev_type, text)
                                elif ev_type == "token":
                                    yield text
            return
        except Exception as error:
            if yielded_content:
                raise
            logger.warning(
                "llm_stream_tier_failed_falling_back",
                extra={"agent_role": agent_role, "tier": spec.key, "error": str(error)},
            )
            last_error = error

    raise RuntimeError(
        f"All local tiers failed to stream for role '{agent_role}'. "
        f"Last error: {last_error}"
    ) from last_error
