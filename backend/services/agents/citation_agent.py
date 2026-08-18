# ============================================================
# GenResearch — Citation Agent
# Extracts and formats citations from research papers
# ============================================================
from services.llm_service import call_llm
from services.rag_service import semantic_search


CITATION_SYSTEM = """You are GenResearch Citation Agent, an expert in academic citation management.
Your task is to extract and format all identifiable references from the provided paper excerpts.

Follow these rules:
1. Extract every reference/citation you can find in the text
2. Format each citation in the requested style (default: APA 7th Edition)
3. If complete information isn't available, include what you have and mark missing fields with [incomplete...]
4. Organize citations alphabetically by first author's last name
5. Include DOI when mentioned
6. Number each citation sequentially
7. At the end, provide a count of total citations found"""


CITATION_STYLES = {
    "apa": "APA 7th Edition (Author, Year. Title. Journal, Volume(Issue), Pages. DOI)",
    "mla": "MLA 9th Edition (Author. \"Title.\" Journal, vol. X, no. X, Year, pp. X-X.)",
    "ieee": "IEEE ([1] Author, \"Title,\" Journal, vol. X, no. X, pp. X-X, Year.)",
    "chicago": "Chicago 17th (Author. \"Title.\" Journal Volume, no. Issue (Year): Pages.)",
}


async def run_citation_extraction(
    user_id: str,
    paper_ids: list[str],
    style: str = "apa",
) -> dict:
    """
    Extract and format citations from papers.
    """
    style_desc = CITATION_STYLES.get(style.lower(), CITATION_STYLES["apa"])
    all_citations: list[dict] = []

    for paper_id in paper_ids:
        # Search for references/bibliography sections
        chunks = await semantic_search(
            user_id=user_id,
            query="references bibliography citations authors doi journal publication year",
            top_k=15,
            paper_id=paper_id,
        )

        if not chunks:
            all_citations.append({
                "paper_id": paper_id,
                "title": "Unknown",
                "citations_text": "No content found for this paper.",
                "count": 0,
                "status": "empty",
            })
            continue

        title = chunks[0].get("title", "Untitled Paper")

        context = "\n\n---\n\n".join(
            f"[Excerpt {i+1}]\n{c['text']}" for i, c in enumerate(chunks)
        )

        prompt = f"""Extract all academic citations and references from the following excerpts of the paper "{title}".

Citation Style Required: {style_desc}

--- PAPER EXCERPTS ---

{context}

--- END OF EXCERPTS ---

Extract and format all citations found:"""

        citations_text = await call_llm(
            prompt=prompt,
            system=CITATION_SYSTEM,
            temperature=0.2,
            max_tokens=3000,
        )

        all_citations.append({
            "paper_id": paper_id,
            "title": title,
            "citations_text": citations_text,
            "style": style.upper(),
            "chunks_used": len(chunks),
            "status": "completed",
        })

    return {
        "agent": "citation",
        "results": all_citations,
        "style": style.upper(),
        "total_papers": len(paper_ids),
    }
