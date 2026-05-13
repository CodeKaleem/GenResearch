"""
Phase 1 Test — Ollama LLM Brain Connector
Run with: python -m pytest tests/test_llm.py -v
"""

import pytest
from app.core.llm import llm
from app.core.config import settings


def test_settings_loaded():
    """Config reads from .env correctly."""
    assert settings.OLLAMA_MODEL == "gemma2:2b"
    assert "11434" in settings.OLLAMA_BASE_URL
    print(f"\n  Model: {settings.OLLAMA_MODEL}")
    print(f"  URL:   {settings.OLLAMA_BASE_URL}")


def test_ollama_is_available():
    """Ollama service is reachable."""
    available = llm.is_available()
    assert available, "Ollama is not running! Start it with: ollama serve"
    print("\n  Ollama is UP and reachable")


def test_list_models():
    """At least one model is available in Ollama."""
    models = llm.list_models()
    assert len(models) > 0, "No models found in Ollama"
    print(f"\n  Available models: {models}")


def test_basic_generation():
    """LLM returns a non-empty response to a simple prompt."""
    response = llm.generate(
        prompt="Reply with exactly one sentence: What is FastAPI?",
        system="You are a helpful assistant. Be concise."
    )
    assert response, "LLM returned empty response"
    assert len(response) > 10, "Response is too short"
    print(f"\n  LLM Response: {response[:200]}")


def test_generation_with_context():
    """LLM uses provided context in its response."""
    context = "GenResearch is a multi-agent AI platform for academic research."
    prompt = f"Context: {context}\n\nQuestion: What is GenResearch in one sentence?"

    response = llm.generate(prompt=prompt)
    assert response, "LLM returned empty response"
    print(f"\n  Contextual Response: {response[:200]}")
