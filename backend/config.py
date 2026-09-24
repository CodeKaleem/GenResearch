import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Settings:
    """
    All configuration lives here. No other config file should be needed.
    Environment variables override defaults.
    """

    # App
    APP_NAME: str = os.getenv("APP_NAME", "GenResearch")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.3.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-dev")

    # Ollama (the only LLM provider)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # Heavy tier
    OLLAMA_HEAVY_MODEL: str = os.getenv("OLLAMA_HEAVY_MODEL", "qwen3:8b")
    OLLAMA_HEAVY_MAX_CONCURRENT: int = int(os.getenv("OLLAMA_HEAVY_MAX_CONCURRENT", "1"))
    OLLAMA_HEAVY_NUM_THREAD: int = int(os.getenv("OLLAMA_HEAVY_NUM_THREAD", "5"))
    OLLAMA_HEAVY_NUM_GPU: int = int(os.getenv("OLLAMA_HEAVY_NUM_GPU", "0"))

    # Mid tier
    OLLAMA_MID_MODEL: str = os.getenv("OLLAMA_MID_MODEL", "qwen3:4b-instruct-2507")
    OLLAMA_MID_MAX_CONCURRENT: int = int(os.getenv("OLLAMA_MID_MAX_CONCURRENT", "2"))
    OLLAMA_MID_NUM_THREAD: int = int(os.getenv("OLLAMA_MID_NUM_THREAD", "2"))
    OLLAMA_MID_NUM_GPU: int = int(os.getenv("OLLAMA_MID_NUM_GPU", "0"))

    # Light tier
    OLLAMA_LIGHT_MODEL: str = os.getenv("OLLAMA_LIGHT_MODEL", "phi4-mini")
    OLLAMA_LIGHT_MAX_CONCURRENT: int = int(os.getenv("OLLAMA_LIGHT_MAX_CONCURRENT", "2"))
    OLLAMA_LIGHT_NUM_THREAD: int = int(os.getenv("OLLAMA_LIGHT_NUM_THREAD", "1"))
    OLLAMA_LIGHT_NUM_GPU: int = int(os.getenv("OLLAMA_LIGHT_NUM_GPU", "0"))
    OLLAMA_HEAVY_CONTEXT: int = int(os.getenv("OLLAMA_HEAVY_CONTEXT", "6000"))
    OLLAMA_MID_CONTEXT: int = int(os.getenv("OLLAMA_MID_CONTEXT", "8000"))
    OLLAMA_LIGHT_CONTEXT: int = int(os.getenv("OLLAMA_LIGHT_CONTEXT", "4000"))

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ChromaDB
    CHROMA_PERSIST_PATH: str = os.getenv(
        "CHROMA_PERSIST_PATH",
        str(Path(__file__).resolve().parent / "chroma_db"),
    )

    # Chunking
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # Academic search APIs, not text generation providers
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")


settings = Settings()
