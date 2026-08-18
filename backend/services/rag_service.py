# ============================================================
# GenResearch — RAG Service
# Retrieval-Augmented Generation using ChromaDB + Mistral 7B
# ============================================================
import httpx
from config import settings
from database.chroma_client import get_user_collection
from services.embedder import embed_single


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
                "distance": results["distances"][0][i],
            })

    return hits


def _build_rag_prompt(query: str, context_chunks: list[dict]) -> str:
    """
    Build a prompt that instructs Mistral to answer based ONLY on the
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
    3. Generate answer via Mistral 7B (Ollama)
    4. Return answer + source references
    """
    # Step 1: Retrieve relevant chunks
    chunks = await semantic_search(user_id, query, top_k, paper_id)

    if not chunks:
        return {
            "answer": "I don't have any documents to search through. Please upload some papers first, and then I can answer your questions based on their content.",
            "sources": [],
            "model": settings.OLLAMA_LLM_MODEL,
        }

    # Step 2: Build the RAG prompt
    prompt = _build_rag_prompt(query, chunks)

    # Step 3: Call Mistral 7B via Ollama
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            url,
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 1024,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    answer = data.get("response", "").strip()

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
        "model": settings.OLLAMA_LLM_MODEL,
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
    import json as json_lib

    # Step 1: Retrieve relevant chunks
    chunks = await semantic_search(user_id, query, top_k, paper_id)

    if not chunks:
        yield json_lib.dumps({
            "type": "answer",
            "content": "I don't have any documents to search through. Please upload some papers first.",
        }) + "\n"
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

    yield json_lib.dumps({"type": "sources", "sources": sources}) + "\n"

    # Step 2: Build the RAG prompt
    prompt = _build_rag_prompt(query, chunks)

    # Step 3: Stream from Mistral 7B
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            url,
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 1024,
                },
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json_lib.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield json_lib.dumps({
                                "type": "token",
                                "content": token,
                            }) + "\n"
                        if data.get("done", False):
                            yield json_lib.dumps({"type": "done"}) + "\n"
                    except json_lib.JSONDecodeError:
                        continue
