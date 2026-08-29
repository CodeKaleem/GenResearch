# ============================================================
# GenResearch — ChromaDB Client (Singleton)
# Persistent local vector store
# ============================================================
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings

_client: chromadb.ClientAPI | None = None


def get_chroma() -> chromadb.ClientAPI:
    """Return a singleton persistent ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_user_collection(user_id: str) -> chromadb.Collection:
    """
    Return (or create) a ChromaDB collection scoped to a specific user.
    Used by the legacy paper-upload pipeline (papers router, chat).
    Collection name: user_{uuid_with_underscores}
    """
    safe_name = f"user_{user_id.replace('-', '_')}"
    client = get_chroma()
    return client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"},
    )


def get_session_collection(session_id: str) -> chromadb.Collection:
    """
    Return (or create) a ChromaDB collection scoped to a pipeline session.
    Chunks ingested for one topic/session never surface in a different session.
    Collection name: session_{uuid_with_underscores}
    """
    safe_name = f"session_{session_id.replace('-', '_')}"
    client = get_chroma()
    return client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"},
    )


def delete_session_collection(session_id: str) -> bool:
    """
    Delete a session-scoped ChromaDB collection (for cleanup/GC).
    Returns True if deleted, False if it didn't exist.
    """
    safe_name = f"session_{session_id.replace('-', '_')}"
    client = get_chroma()
    try:
        client.delete_collection(safe_name)
        return True
    except Exception:
        return False
