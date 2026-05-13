"""
Ollama LLM Brain Connector
--------------------------
This module is the single interface between GenResearch and the local LLM.
All agents call this — never call Ollama directly from agent code.
"""

import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class OllamaLLM:
    """
    Wrapper around the Ollama REST API.
    Provides synchronous and streaming generation.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = 120.0  # 2 min timeout — gemma2:2b is slow on CPU

    def generate(self, prompt: str, system: str = "") -> str:
        """
        Send a prompt to the local LLM and return the response.

        Args:
            prompt: The user prompt / task instruction
            system: Optional system prompt to guide model behaviour

        Returns:
            The model's text response as a string

        Raises:
            RuntimeError: If Ollama is unreachable or returns an error
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        logger.info(
            "llm_request",
            model=self.model,
            prompt_length=len(prompt),
            has_system=bool(system),
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("response", "").strip()

                logger.info(
                    "llm_response",
                    model=self.model,
                    response_length=len(result),
                    done=data.get("done", False),
                )

                return result

        except httpx.ConnectError:
            logger.error("llm_connection_failed", url=self.base_url)
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is 'ollama serve' running?"
            )

        except httpx.TimeoutException:
            logger.error("llm_timeout", timeout=self.timeout)
            raise RuntimeError(
                f"Ollama request timed out after {self.timeout}s. "
                "Try a shorter prompt or restart Ollama."
            )

        except httpx.HTTPStatusError as e:
            logger.error("llm_http_error", status=e.response.status_code)
            raise RuntimeError(f"Ollama returned HTTP {e.response.status_code}")

    def is_available(self) -> bool:
        """
        Health check — returns True if Ollama is reachable.
        Used by the FastAPI /health endpoint.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """
        Returns list of models available in Ollama.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# Single instance — import this everywhere
llm = OllamaLLM()
