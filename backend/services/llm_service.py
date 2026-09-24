from __future__ import annotations

import asyncio
import json
import logging
import hashlib
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


def _chat_completions_url() -> str:
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    return f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"


def _semaphore(spec: ModelSpec) -> asyncio.Semaphore:
    if spec.key not in _semaphores:
        _semaphores[spec.key] = asyncio.Semaphore(spec.max_concurrent)
    return _semaphores[spec.key]


def _is_retryable(error: BaseException) -> bool:
    status = getattr(getattr(error, "response", None), "status_code", None)
    if status in (500, 502, 503, 504):
        return True
    return isinstance(error, httpx.TimeoutException)


@retry(
    stop=stop_after_attempt(3),
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
        "model": spec.model_id,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "num_ctx": context_limit or spec.num_ctx,
    }

    async with _semaphore(spec):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    _chat_completions_url(),
                    headers={"Authorization": "Bearer ollama"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip(), data.get("usage", {}) or {}
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
                tokens_used=int(usage.get("total_tokens") or 0),
                user_id=request_context.get_user_id(),
            )
            tracking.log_audit_event(
                node_name=agent_role,
                model_used=spec.model_id,
                prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                tokens_in=int(usage.get("prompt_tokens") or 0),
                tokens_out=int(usage.get("completion_tokens") or 0),
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
            logger.error(
                "llm_unexpected_error",
                extra={"agent_role": agent_role, "tier": spec.key, "error": str(error)},
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
    for spec in chain:
        payload = {
            "model": spec.model_id,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "num_ctx": context_limit or spec.num_ctx,
        }
        try:
            async with _semaphore(spec):
                async with httpx.AsyncClient(timeout=180.0) as client:
                    async with client.stream(
                        "POST",
                        _chat_completions_url(),
                        headers={"Authorization": "Bearer ollama"},
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line.removeprefix("data:").strip()
                            if data == "[DONE]":
                                return
                            chunk = json.loads(data)
                            content = chunk["choices"][0].get("delta", {}).get("content")
                            if content:
                                yield content
            return
        except Exception as error:
            logger.warning(
                "llm_stream_tier_failed_falling_back",
                extra={"agent_role": agent_role, "tier": spec.key, "error": str(error)},
            )
            last_error = error

    raise RuntimeError(
        f"All local tiers failed to stream for role '{agent_role}'. "
        f"Last error: {last_error}"
    ) from last_error
