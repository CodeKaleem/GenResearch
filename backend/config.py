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
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # Ollama (the only LLM provider)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_REQUEST_TIMEOUT: float = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "600"))
    OLLAMA_JUDGE_CONTEXT: int = int(os.getenv("OLLAMA_JUDGE_CONTEXT", "8192"))
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    OLLAMA_EMBED_PREFIXES: bool = os.getenv("OLLAMA_EMBED_PREFIXES", "false").lower() in ("true", "1", "yes")
    # How long Ollama keeps a model in memory after its last request. Without this
    # Ollama's default (5 min) unloads models between questions and every chat
    # pays a cold-load penalty.
    OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    # Per-read timeout for chat streaming. The generic 600s timeout means a stuck
    # model blocks the user for 10 minutes before the fallback tier is tried.
    OLLAMA_CHAT_READ_TIMEOUT: float = float(os.getenv("OLLAMA_CHAT_READ_TIMEOUT", "120"))

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

    # Document structure and chat routing
    DOC_STRUCTURE_ON_UPLOAD: bool = os.getenv("DOC_STRUCTURE_ON_UPLOAD", "True").lower() in ("true", "1", "yes")
    CHAT_INTENT_ROUTING: bool = os.getenv("CHAT_INTENT_ROUTING", "True").lower() in ("true", "1", "yes")
    DOC_STRUCTURE_VERSION: str = os.getenv("DOC_STRUCTURE_VERSION", "1")
    CHAT_MAP_MAX_CONCURRENCY: int = int(os.getenv("CHAT_MAP_MAX_CONCURRENCY", "2"))
    CHAT_MAP_WINDOW_CHARS: int = int(os.getenv("CHAT_MAP_WINDOW_CHARS", str(max(2000, OLLAMA_MID_CONTEXT // 3))))

    # Chat retrieval quality
    CHAT_TOP_K: int = int(os.getenv("CHAT_TOP_K", "14"))                    # floor for the UI's top_k
    CHAT_BROAD_TOP_K: int = int(os.getenv("CHAT_BROAD_TOP_K", "20"))       # summary/gaps/contributions...
    CHAT_FETCH_MULTIPLIER: int = int(os.getenv("CHAT_FETCH_MULTIPLIER", "3"))  # over-fetch before filtering references
    CHAT_MAX_DISTANCE: float = float(os.getenv("CHAT_MAX_DISTANCE", "0.82"))   # cosine distance cutoff, 0 disables
    CHAT_HISTORY_TURNS: int = int(os.getenv("CHAT_HISTORY_TURNS", "6"))
    CHAT_CONTEXT_CHARS: int = int(os.getenv("CHAT_CONTEXT_CHARS", "24000"))    # evidence budget per prompt

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
