# ============================================================
# GenResearch — RAG Service
# Retrieval-Augmented Generation using ChromaDB and the shared LLM client
# ============================================================
import json
from config import settings
from database.chroma_client import get_user_collection, get_session_collection
from services.embedder import embed_single
from services.llm_service import call_llm, call_llm_stream


async def semantic_search(
    user_id: str,
    query: str,
    top_k: int = 5,
    paper_id: str | None = None,
) -> list[dict]:
    """
    Embed the user's query with nomic-embed-text, then query ChromaDB
    for the top-k most similar chunks from the user's collection.

    Optionally filter by a specific paper_id.
    Returns a list of dicts: {text, paper_id, title, chunk_index, distance}
    """
    query_embedding = await embed_single(query)
    collection = get_user_collection(user_id)

    if collection.count() == 0:
        return []

    where_filter = {"paper_id": paper_id} if paper_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "id": doc_id,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "paper_id": results["metadatas"][0][i].get("paper_id", ""),
                "title": results["metadatas"][0][i].get("title", "Unknown"),
                "chunk_index": results["metadatas"][0][i].get("chunk_index", 0),
                "chunk_id": results["metadatas"][0][i].get("chunk_id", doc_id),
                "page": results["metadatas"][0][i].get("page"),
                "distance": results["distances"][0][i],
            })

    return hits


async def semantic_search_session(
    session_id: str,
    query: str,
    top_k: int = 5,
    source_ids: list[str] | None = None,
) -> list[dict]:
    """
    Session-scoped semantic search for the pipeline draft node.
    Queries ONLY the session's ChromaDB collection — guarantees
    that chunks from different topics/sessions never leak.
    """
    if source_ids is not None and not source_ids:
        return []

    query_embedding = await embed_single(query)
    collection = get_session_collection(session_id)

    if collection.count() == 0:
        return []

    where_filter = {"source_id": {"$in": source_ids}} if source_ids is not None else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "id": doc_id,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "source_id": results["metadatas"][0][i].get("source_id", ""),
                "title": results["metadatas"][0][i].get("title", "Unknown"),
                "chunk_index": results["metadatas"][0][i].get("chunk_index", 0),
                "distance": results["distances"][0][i],
            })

    return hits


def _build_rag_prompt(query: str, context_chunks: list[dict]) -> str:
    """
    Build a prompt that instructs the chat model to answer based ONLY on the
    retrieved document context.
    """
    context_parts: list[str] = []
    for i, chunk in enumerate(context_chunks, 1):
        source = chunk.get("title", "Unknown Document")
        text = chunk.get("text", "")
        context_parts.append(
            f"[Source {i}: {source}]\n{text}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are GenResearch AI, an academic research assistant. Answer the user's question based ONLY on the provided document excerpts below.

Rules:
1. Use ONLY the information from the provided sources to answer.
2. If the answer is not found in the sources, say "I couldn't find information about this in your uploaded documents."
3. Cite which source(s) you used by referencing the source number, e.g. [Source 1].
4. Be concise, accurate, and academic in tone.
5. If multiple sources contain relevant information, synthesize them together.

--- DOCUMENT EXCERPTS ---

{context_block}

--- END OF EXCERPTS ---

User Question: {query}

Answer:"""

    return prompt


async def generate_answer(
    user_id: str,
    query: str,
    top_k: int = 5,
    paper_id: str | None = None,
) -> dict:
    """
    Full RAG pipeline:
    1. Semantic search for relevant chunks
    2. Build context-augmented prompt
    3. Generate an answer through the shared local LLM service
    4. Return answer + source references
    """
    # Step 1: Retrieve relevant chunks
    chunks = await semantic_search(user_id, query, top_k, paper_id)

    if not chunks:
        return {
            "answer": "I don't have any documents to search through. Please upload some papers first, and then I can answer your questions based on their content.",
            "sources": [],
            "chunks_used": 0,
            "model": settings.OLLAMA_MID_MODEL,
        }

    # Step 2: Build the RAG prompt
    prompt = _build_rag_prompt(query, chunks)

    answer = await call_llm(
        prompt,
        agent_role="chat",
        temperature=0.3,
        max_tokens=1024,
    )

    # Step 4: Build source references
    seen_papers: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        pid = chunk["paper_id"]
        if pid not in seen_papers:
            seen_papers.add(pid)
            sources.append({
                "paper_id": pid,
                "title": chunk["title"],
                "relevance": round(1 - chunk["distance"], 4),  # cosine similarity
            })

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(chunks),
        "model": settings.OLLAMA_MID_MODEL,
    }


async def generate_answer_stream(
    user_id: str,
    query: str,
    top_k: int = 5,
    paper_id: str | None = None,
):
    """
    Streaming version of the RAG pipeline.
    Yields chunks of text as they come from Mistral 7B.
    """
    # Step 1: Retrieve relevant chunks
    chunks = await semantic_search(user_id, query, top_k, paper_id)

    if not chunks:
        yield json.dumps({"type": "sources", "sources": []}) + "\n"
        yield json.dumps({
            "type": "token",
            "content": "I don't have any documents to search through. Please upload some papers first.",
        }) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    # Yield source info first
    seen_papers: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        pid = chunk["paper_id"]
        if pid not in seen_papers:
            seen_papers.add(pid)
            sources.append({
                "paper_id": pid,
                "title": chunk["title"],
                "relevance": round(1 - chunk["distance"], 4),
            })

    yield json.dumps({"type": "sources", "sources": sources}) + "\n"

    # Step 2: Build the RAG prompt
    prompt = _build_rag_prompt(query, chunks)

    async for token in call_llm_stream(
        prompt,
        agent_role="chat",
        temperature=0.3,
        max_tokens=1024,
    ):
        if token:
            yield json.dumps({"type": "token", "content": token}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"
