# ============================================================
# GenResearch — LLM Service (NVIDIA NIM Router)
# Role-based model selection via OpenAI-compatible NIM API.
#
# Design rules (from Master Spec §2):
#   - All text-generation goes through NVIDIA NIM, never local Ollama.
#   - Embeddings stay on local Ollama (handled by embedder.py).
#   - Draft Agent → nemotron-3.5-lightning-30b-a3b
#   - All evaluators/critics/questionnaire → nemotron-3-nano
#   - Citation verification MUST use a different model than Draft.
#   - Rate limit: ~35 req/min per model (free tier ceiling).
# ============================================================
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

# ── Agent Role → Model Mapping ───────────────────────────────
# Deliberately chosen per spec §2.2. Not arbitrary.
ROLE_MODEL_MAP: dict[str, str] = {
    # Heavy reasoning / long-form generation
    "draft": settings.NVIDIA_DRAFT_MODEL,

    # Cheap / fast for evaluation, critique, questionnaire
    "questionnaire": settings.NVIDIA_EVAL_MODEL,
    "sufficiency_evaluator": settings.NVIDIA_EVAL_MODEL,
    "gap_report": settings.NVIDIA_EVAL_MODEL,
    "outline_plan": settings.NVIDIA_EVAL_MODEL,
    "source_quality_evaluator": settings.NVIDIA_EVAL_MODEL,
    "citation_verification": settings.NVIDIA_EVAL_MODEL,
    "section_critic": settings.NVIDIA_EVAL_MODEL,
    "final_qa": settings.NVIDIA_EVAL_MODEL,
}


# ── Per-Model Rate Limiter ───────────────────────────────────
class _TokenBucketLimiter:
    """
    Simple async token-bucket rate limiter.
    Ensures we stay under NIM's ~40 req/min free-tier ceiling.
    """

    def __init__(self, max_rpm: int):
        self._interval = 60.0 / max_rpm  # seconds between allowed requests
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_request_time)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_time = time.monotonic()


# One limiter per model to track independently
_limiters: dict[str, _TokenBucketLimiter] = {}


def _get_limiter(model: str) -> _TokenBucketLimiter:
    if model not in _limiters:
        _limiters[model] = _TokenBucketLimiter(settings.NIM_MAX_RPM)
    return _limiters[model]


# ── NIM Client (singleton) ───────────────────────────────────
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.NVIDIA_API_KEY:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. "
                "Set it in backend/.env to use NVIDIA NIM for text generation."
            )
        _client = AsyncOpenAI(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
        )
    return _client


# ── Public API ───────────────────────────────────────────────

def get_model_for_role(agent_role: str) -> str:
    """
    Resolve an agent role to the model it should use.
    Raises ValueError if the role is unknown.
    """
    model = ROLE_MODEL_MAP.get(agent_role)
    if model is None:
        raise ValueError(
            f"Unknown agent role '{agent_role}'. "
            f"Valid roles: {sorted(ROLE_MODEL_MAP.keys())}"
        )
    return model


async def call_llm(
    prompt: str,
    *,
    agent_role: str,
    system: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    response_format: dict | None = None,
) -> str:
    """
    Send a prompt to NVIDIA NIM and return the full response text.

    Args:
        prompt:          The user message / task instruction.
        agent_role:      Which agent is calling (determines model selection).
        system:          System prompt to guide model behavior.
        temperature:     Sampling temperature.
        max_tokens:      Maximum tokens to generate.
        response_format: Optional response format (e.g. {"type": "json_object"}).

    Returns:
        The model's text response as a string.
    """
    model = get_model_for_role(agent_role)
    client = _get_client()
    limiter = _get_limiter(model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    logger.info(
        "llm_request",
        extra={
            "agent_role": agent_role,
            "model": model,
            "prompt_length": len(prompt),
            "has_system": bool(system),
        },
    )

    await limiter.acquire()

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = await client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content.strip()

        logger.info(
            "llm_response",
            extra={
                "agent_role": agent_role,
                "model": model,
                "response_length": len(result),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            },
        )
        return result

    except Exception as e:
        logger.error(
            "llm_error",
            extra={"agent_role": agent_role, "model": model, "error": str(e)},
        )
        raise RuntimeError(
            f"NIM call failed for role '{agent_role}' (model: {model}): {e}"
        ) from e


async def call_llm_stream(
    prompt: str,
    *,
    agent_role: str,
    system: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream tokens from NVIDIA NIM. Yields raw token strings.

    Same arguments as call_llm (minus response_format).
    """
    model = get_model_for_role(agent_role)
    client = _get_client()
    limiter = _get_limiter(model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    logger.info(
        "llm_stream_request",
        extra={"agent_role": agent_role, "model": model, "prompt_length": len(prompt)},
    )

    await limiter.acquire()

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(
            "llm_stream_error",
            extra={"agent_role": agent_role, "model": model, "error": str(e)},
        )
        raise RuntimeError(
            f"NIM stream failed for role '{agent_role}' (model: {model}): {e}"
        ) from e
