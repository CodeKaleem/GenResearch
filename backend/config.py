# ============================================================
# GenResearch — Unified Configuration
# Single source of truth for all settings across the backend.
# ============================================================
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Settings:
    """
    All configuration lives here. No other config file should be needed.
    Environment variables override defaults.
    """

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = os.getenv("APP_NAME", "GenResearch")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.2.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-dev")

    # ── NVIDIA NIM (text generation) ─────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "nvidia")
    NVIDIA_BASE_URL: str = os.getenv(
        "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
    )
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_DRAFT_MODEL: str = os.getenv(
        "NVIDIA_DRAFT_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"
    )
    NVIDIA_EVAL_MODEL: str = os.getenv(
        "NVIDIA_EVAL_MODEL", "nvidia/nemotron-3-nano-30b-a3b"
    )

    # ── Ollama (embeddings ONLY) ─────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # ── Supabase ─────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ── ChromaDB ─────────────────────────────────────────────
    CHROMA_PERSIST_PATH: str = os.getenv(
        "CHROMA_PERSIST_PATH",
        str(Path(__file__).resolve().parent / "chroma_db"),
    )

    # ── Chunking ─────────────────────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # ── Academic APIs (source gathering) ─────────────────────
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ── Rate Limiting ────────────────────────────────────────
    # NIM free tier: ~40 req/min per model. We target 35 to stay safe.
    NIM_MAX_RPM: int = int(os.getenv("NIM_MAX_RPM", "35"))


settings = Settings()
