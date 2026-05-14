# ============================================================
# GenResearch — Backend Configuration
# Central config loaded from environment variables
# ============================================================
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend root
load_dotenv(Path(__file__).resolve().parent / ".env")


class Settings:
    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ── Ollama ────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # ── ChromaDB ──────────────────────────────────────────────
    CHROMA_PERSIST_PATH: str = os.getenv(
        "CHROMA_PERSIST_PATH",
        str(Path(__file__).resolve().parent / "chroma_db"),
    )

    # ── Chunking ──────────────────────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = os.getenv("APP_NAME", "GenResearch")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")


settings = Settings()
