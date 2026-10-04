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


def _request_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        connect=10.0,
        read=settings.OLLAMA_REQUEST_TIMEOUT,
        write=30.0,
        pool=30.0,
    )


def _request_payload(
    spec: ModelSpec,
    messages: list[dict],
    *,
    stream: bool,
    temperature: float,
    max_tokens: int,
    context_limit: int | None,
) -> dict:
    payload = {
        "model": spec.model_id,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": context_limit or spec.num_ctx,
            "num_thread": spec.num_thread,
            "num_gpu": spec.num_gpu,
        },
    }
    if spec.think is not None:
        payload["think"] = spec.think
    return payload


def _strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def _partial_tag_suffix_length(text: str, tag: str) -> int:
    lowered = text.lower()
    for length in range(min(len(text), len(tag) - 1), 0, -1):
        if lowered.endswith(tag[:length].lower()):
            return length
    return 0


def _filter_think_chunk(content: str, state: dict, *, final: bool = False) -> str:
    data = state.get("pending", "") + content
    output: list[str] = []
    while data:
        lowered = data.lower()
        if state.get("inside_think", False):
            closing = lowered.find("</think>")
            if closing < 0:
                suffix_length = 0 if final else _partial_tag_suffix_length(data, "</think>")
                state["pending"] = data[-suffix_length:] if suffix_length else ""
                return "".join(output)
            data = data[closing + len("</think>"):]
            state["inside_think"] = False
            continue

        opening = lowered.find("<think>")
        if opening >= 0:
            output.append(data[:opening])
            data = data[opening + len("<think>"):]
            state["inside_think"] = True
            continue
        if final:
            output.append(data)
            data = ""
            state["pending"] = ""
            break
        suffix_length = _partial_tag_suffix_length(data, "<think>")
        safe_length = len(data) - suffix_length
        output.append(data[:safe_length])
        state["pending"] = data[safe_length:]
        break
    return "".join(output)


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
            async with httpx.AsyncClient(timeout=_request_timeout()) as client:
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
            result, usage = await _call_ollama_once(spec, messages, temperature, max_tokens, context_limit)
            logger.info(
                "llm_response",
                extra={
                    "agent_role": agent_role,
                    "tier": spec.key,
                    "response_length": len(result),
                },
            )
            tracking.log_api_cost(
                agent=agent_role,
                model=spec.model_id,
                tokens_used=int(usage.get("prompt_eval_count") or 0)
                + int(usage.get("eval_count") or 0),
                user_id=request_context.get_user_id(),
            )
            tracking.log_audit_event(
                node_name=agent_role,
                model_used=spec.model_id,
                prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                tokens_in=int(usage.get("prompt_eval_count") or 0),
                tokens_out=int(usage.get("eval_count") or 0),
                latency_ms=int((time.perf_counter() - started_at) * 1000),
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
) -> AsyncIterator[str]:
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
                async with httpx.AsyncClient(timeout=_request_timeout()) as client:
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
                            content = chunk.get("message", {}).get("content", "")
                            visible = _filter_think_chunk(content, think_state)
                            if visible:
                                yielded_content = True
                                yield visible
                            if chunk.get("done"):
                                break
                        remaining = _filter_think_chunk("", think_state, final=True)
                        if remaining:
                            yielded_content = True
                            yield remaining
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
