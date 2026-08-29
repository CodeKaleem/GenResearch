# ============================================================
# GenResearch — ChromaDB Service
# Store, retrieve, and delete paper chunks in ChromaDB
# ============================================================
from database.chroma_client import get_user_collection, get_session_collection
from services.embedder import embed_texts


async def store_chunks(
    user_id: str,
    paper_id: str,
    chunks: list[str],
    title: str,
    collection_name: str,
) -> int:
    """
    Embed and store text chunks in the user's ChromaDB collection.
    Used by the legacy paper-upload pipeline (papers router).
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    # Generate embeddings for all chunks
    embeddings = await embed_texts(chunks)

    # Build IDs, documents, metadata, and embeddings lists
    ids = [f"{paper_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "paper_id": paper_id,
            "user_id": user_id,
            "chunk_index": i,
            "title": title,
            "collection": collection_name,
        }
        for i in range(len(chunks))
    ]

    # Upsert into ChromaDB
    col = get_user_collection(user_id)
    col.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


async def store_chunks_session(
    session_id: str,
    source_id: str,
    chunks: list[str],
    title: str,
    tag: str = "scraped",
) -> int:
    """
    Embed and store text chunks in a session-scoped ChromaDB collection.
    Used by the pipeline ingestion node — guarantees topic isolation.
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    embeddings = await embed_texts(chunks)

    ids = [f"{source_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source_id": source_id,
            "session_id": session_id,
            "chunk_index": i,
            "title": title,
            "tag": tag,
        }
        for i in range(len(chunks))
    ]

    col = get_session_collection(session_id)
    col.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def delete_paper_chunks(user_id: str, paper_id: str) -> int:
    """
    Delete all chunks belonging to a paper from the user's collection.
    Returns the number of chunks deleted.
    """
    col = get_user_collection(user_id)

    # Find all chunk IDs for this paper
    results = col.get(where={"paper_id": paper_id}, include=[])
    chunk_ids = results.get("ids", [])

    if chunk_ids:
        col.delete(ids=chunk_ids)

    return len(chunk_ids)
