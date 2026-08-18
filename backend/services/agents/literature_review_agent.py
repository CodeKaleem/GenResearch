# ============================================================
# GenResearch — Literature Review Agent
# Generates comparative literature reviews from multiple papers
# ============================================================
from services.llm_service import call_llm
from services.rag_service import semantic_search


LITERATURE_REVIEW_SYSTEM = """You are GenResearch Literature Review Agent, an expert in synthesizing
academic literature. Your task is to produce a coherent literature review from multiple research papers.

Follow these rules:
1. Structure the review with: **Introduction**, **Thematic Analysis**, **Research Gaps**, **Synthesis & Discussion**, **Conclusion**
2. Compare and contrast findings across different papers
3. Identify common themes, contradictions, and research gaps
4. Use proper academic citation style: refer to papers by their title or author when mentioned in excerpts
5. Maintain a scholarly, analytical tone
6. Aim for 600-1000 words
7. Highlight areas where further research is needed
8. Connect ideas across papers to show the evolution of the field"""


async def run_literature_review(
    user_id: str,
    paper_ids: list[str],
    focus_topic: str = "",
) -> dict:
    """
    Generate a comparative literature review from multiple papers.
    Uses RAG to retrieve relevant content and synthesizes across papers.
    """
    all_chunks: list[dict] = []
    paper_titles: list[str] = []

    search_query = focus_topic if focus_topic else "research findings methodology results contributions"

    for paper_id in paper_ids:
        chunks = await semantic_search(
            user_id=user_id,
            query=search_query,
            top_k=10,
            paper_id=paper_id,
        )
        if chunks:
            all_chunks.extend(chunks)
            title = chunks[0].get("title", "Untitled")
            if title not in paper_titles:
                paper_titles.append(title)

    if not all_chunks:
        return {
            "agent": "literature_review",
            "review": "No content found in the selected papers.",
            "papers_analyzed": 0,
            "status": "empty",
        }

    # Sort chunks by relevance (distance)
    all_chunks.sort(key=lambda c: c.get("distance", 1.0))
    top_chunks = all_chunks[:20]  # Use top 20 most relevant chunks

    context = "\n\n---\n\n".join(
        f"[Paper: {c.get('title', 'Unknown')} | Excerpt {i+1}]\n{c['text']}"
        for i, c in enumerate(top_chunks)
    )

    topic_instruction = f'Focus the review on the topic: "{focus_topic}".' if focus_topic else "Cover the main themes across all papers."

    prompt = f"""Generate a comprehensive literature review based on the following excerpts from {len(paper_titles)} research paper(s).

Papers being reviewed:
{chr(10).join(f"- {t}" for t in paper_titles)}

{topic_instruction}

--- PAPER EXCERPTS ---

{context}

--- END OF EXCERPTS ---

Generate the literature review now:"""

    review_text = await call_llm(
        prompt=prompt,
        system=LITERATURE_REVIEW_SYSTEM,
        temperature=0.4,
        max_tokens=3000,
    )

    return {
        "agent": "literature_review",
        "review": review_text,
        "papers_analyzed": len(paper_titles),
        "paper_titles": paper_titles,
        "chunks_used": len(top_chunks),
        "focus_topic": focus_topic,
        "status": "completed",
    }
