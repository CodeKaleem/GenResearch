# ============================================================
# GenResearch — Summarization Agent
# Generates structured summaries of research papers using RAG
# ============================================================
from services.llm_service import call_llm
from services.rag_service import semantic_search


SUMMARIZATION_SYSTEM = """You are GenResearch Summarization Agent, an expert academic summarizer.
Your task is to produce a comprehensive, well-structured summary of a research paper based on the
provided document excerpts. Follow these rules:

1. Structure the summary with clear sections: **Overview**, **Key Findings**, **Methodology**, **Conclusions**
2. Be thorough but concise — aim for 400-600 words
3. Use academic language and maintain the original paper's tone
4. Cite specific data points, statistics, or claims when found in the excerpts
5. If information for a section is not available, note it briefly and move on
6. End with a "Key Takeaways" bullet list (3-5 points)"""


async def run_summarization(
    user_id: str,
    paper_ids: list[str],
) -> dict:
    """
    Summarize one or more papers. For each paper, retrieves chunks via
    semantic search and generates a structured summary.
    Returns a dict with summaries list and metadata.
    """
    summaries: list[dict] = []

    for paper_id in paper_ids:
        # Retrieve extensive chunks for this paper
        chunks = await semantic_search(
            user_id=user_id,
            query="comprehensive overview key findings methodology results conclusions",
            top_k=15,
            paper_id=paper_id,
        )

        if not chunks:
            summaries.append({
                "paper_id": paper_id,
                "title": "Unknown",
                "summary": "No content found for this paper. It may not be indexed yet.",
                "status": "empty",
            })
            continue

        title = chunks[0].get("title", "Untitled Paper")

        # Build context from chunks
        context = "\n\n---\n\n".join(
            f"[Excerpt {i+1}]\n{c['text']}" for i, c in enumerate(chunks)
        )

        prompt = f"""Based on the following excerpts from the paper "{title}", generate a comprehensive structured summary.

--- PAPER EXCERPTS ---

{context}

--- END OF EXCERPTS ---

Generate the summary now:"""

        summary_text = await call_llm(
            prompt=prompt,
            system=SUMMARIZATION_SYSTEM,
            temperature=0.3,
            max_tokens=2048,
        )

        summaries.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary_text,
            "chunks_used": len(chunks),
            "status": "completed",
        })

    return {
        "agent": "summarization",
        "summaries": summaries,
        "total_papers": len(paper_ids),
    }
