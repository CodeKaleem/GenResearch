# ============================================================
# GenResearch — LLM Service
# Shared async wrapper for Ollama Mistral 7B calls
# ============================================================
import httpx
import json as json_lib
from config import settings


async def call_llm(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    system: str | None = None,
) -> str:
    """
    Call Mistral 7B via Ollama and return the full response text.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"

    full_prompt = prompt
    if system:
        full_prompt = f"[INST] {system}\n\n{prompt} [/INST]"

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            url,
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    return data.get("response", "").strip()


async def call_llm_stream(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    system: str | None = None,
):
    """
    Stream tokens from Mistral 7B. Yields raw token strings.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"

    full_prompt = prompt
    if system:
        full_prompt = f"[INST] {system}\n\n{prompt} [/INST]"

    async with httpx.AsyncClient(timeout=600.0) as client:
        async with client.stream(
            "POST",
            url,
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": full_prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_predict": max_tokens,
                },
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json_lib.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            return
                    except json_lib.JSONDecodeError:
                        continue
