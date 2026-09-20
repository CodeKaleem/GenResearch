import asyncio
import json

# ============================================================
# GenResearch — Summarization Agent (v2)
#
# Changes vs v1:
#   1. Section-wise retrieval (6 targeted queries) instead of one generic
#      query, so limitations / challenges / discussion are not skipped.
#   2. Chunks are merged, de-duplicated and re-ordered by page so the model
#      reads the paper in document order, with page numbers on each excerpt.
#   3. A cheap extraction step classifies the paper (review / empirical / ...)
#      and pulls out explicit figures, so the template fits the paper type.
#   4. Grounding rules: use only the excerpts, copy numbers exactly, keep the
#      authors' hedging, cite excerpts inline as [E3].
#   5. A verification pass fact-checks the draft against the excerpts.
#   6. One failing paper no longer breaks the whole batch; concurrency capped.
#
# Assumptions about semantic_search results (adjust the keys if yours differ):
#   each chunk is a dict with "text", and ideally "title", "page",
#   "chunk_id" and "chunk_index".
# ============================================================
from services.llm_service import call_llm
from services.rag_service import semantic_search


TOP_K_PER_QUERY = 5
MAX_CONCURRENT_PAPERS = 3

# One query per part of a paper. Retrieval by section keeps coverage broad,
# which a single "comprehensive overview" query cannot do.
SECTION_QUERIES = {
    "overview": "abstract introduction research objectives scope research questions",
    "methodology": "method methodology study design data collection sample participants search strategy inclusion criteria",
    "results": "results findings analysis statistics number of studies table figure",
    "discussion": "discussion implications trends future research directions",
    "challenges_limits": "challenges limitations threats to validity ethical issues future work",
    "conclusion": "conclusion conclusions contributions summary",
}

BASE_RULES = """You are GenResearch Summarization Agent, an expert academic summarizer.
Write a summary of a research paper using ONLY the provided excerpts.

Rules:
1. Never add outside knowledge and never infer numbers. Copy numbers, dates, counts and names exactly as written.
2. If excerpts disagree with each other on a figure, say so instead of picking one.
3. Preserve the authors' hedging. Separate what was measured from what was suggested, and do not claim effects the paper did not test.
4. Cite excerpts inline like [E3] after each specific claim or figure.
5. If the excerpts do not cover something the structure asks for, write "Not found in the provided excerpts." instead of guessing.
6. Always include the paper's stated limitations and challenges when they appear.
7. Use academic language and keep the original paper's tone.
8. End with a "Key Takeaways" bullet list (3-5 points)."""

TEMPLATES = {
    "review": (
        "**Overview** (scope, time span, databases, how many papers were screened and included)\n"
        "**Classification / Key Findings** (categories or taxonomy the review uses, with counts)\n"
        "**Trends and Gaps**\n"
        "**Challenges and Limitations** (of the field and of the review itself)\n"
        "**Conclusions**"
    ),
    "empirical": (
        "**Overview** (problem and research questions)\n"
        "**Methodology** (data, sample, methods)\n"
        "**Results** (quantified where possible)\n"
        "**Limitations**\n"
        "**Conclusions**"
    ),
    "theoretical": (
        "**Overview** (problem and contribution)\n"
        "**Core Argument or Framework**\n"
        "**Implications**\n"
        "**Limitations**\n"
        "**Conclusions**"
    ),
    "other": (
        "**Overview**\n"
        "**Key Findings**\n"
        "**Methodology**\n"
        "**Limitations**\n"
        "**Conclusions**"
    ),
}


def _parse_json(text: str) -> dict:
    """Best-effort JSON extraction from an LLM reply. Returns {} on failure."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        parsed = json.loads(text[start:end])
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}


async def _retrieve_chunks(user_id: str, paper_id: str) -> list:
    """Run one search per section, merge, de-duplicate, order by page."""
    results = await asyncio.gather(
        *(
            semantic_search(
                user_id=user_id,
                query=query,
                top_k=TOP_K_PER_QUERY,
                paper_id=paper_id,
            )
            for query in SECTION_QUERIES.values()
        )
    )

    seen = set()
    merged = []
    for chunks in results:
        for chunk in chunks or []:
            key = chunk.get("chunk_id") or hash(chunk.get("text", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)

    # Document order, not similarity order.
    merged.sort(key=lambda c: (c.get("page") or 0, c.get("chunk_index") or 0))
    return merged


def _build_context(chunks: list) -> str:
    return "\n\n---\n\n".join(
        f"[E{i + 1} | page {c.get('page', '?')}]\n{c['text']}"
        for i, c in enumerate(chunks)
    )


async def _extract_profile(context: str) -> dict:
    """Classify the paper and pull out figures that are stated explicitly."""
    prompt = f"""From the excerpts below, return ONLY a JSON object with these keys:
"paper_type": one of "review", "empirical", "theoretical", "other"
"title": string or null
"authors": list of strings (empty if not stated)
"year": integer or null
"key_figures": list of short strings, each an explicit number, count or date with what it refers to, e.g. "100 papers selected from 142 screened"
Use null or empty values when something is not stated. Do not guess.

--- EXCERPTS ---
{context}
--- END OF EXCERPTS ---"""

    raw = await call_llm(
        prompt=prompt,
        agent_role="summarization",
        system="You extract facts from text and reply with strict JSON only.",
        temperature=0.0,
        max_tokens=600,
    )
    return _parse_json(raw)


async def _draft_summary(title: str, profile: dict, context: str, target_words: int) -> str:
    paper_type = profile.get("paper_type")
    template = TEMPLATES.get(paper_type, TEMPLATES["other"])
    figures = "\n".join(f"- {f}" for f in profile.get("key_figures") or [])

    system = (
        f"{BASE_RULES}\n\n"
        f"Structure the summary with these sections:\n{template}\n\n"
        f"Target length: about {target_words} words."
    )
    prompt = f"""Paper: "{title}"

Figures stated in the excerpts (use exactly as written):
{figures or "- none extracted"}

--- PAPER EXCERPTS ---
{context}
--- END OF EXCERPTS ---

Write the summary now:"""

    return await call_llm(
        prompt=prompt,
        agent_role="summarization",
        system=system,
        temperature=0.2,
        max_tokens=2048,
    )


async def _verify_summary(draft: str, context: str) -> dict:
    """Fact-check the draft against the excerpts and return a corrected version."""
    prompt = f"""Fact-check the SUMMARY against the EXCERPTS.
For every number, date, count, ranking, trend claim and outcome claim in the summary, check that the excerpts support it.

Return ONLY a JSON object:
{{"issues": [{{"claim": "...", "problem": "..."}}], "corrected_summary": "..."}}

In corrected_summary, fix or remove unsupported claims, restore any hedging the excerpts contain, and keep the same structure and citations. If nothing is wrong, return the summary unchanged with an empty issues list.

--- EXCERPTS ---
{context}
--- END OF EXCERPTS ---

--- SUMMARY ---
{draft}
--- END OF SUMMARY ---"""

    raw = await call_llm(
        prompt=prompt,
        agent_role="summarization",
        system="You are a strict fact-checker. Reply with JSON only.",
        temperature=0.0,
        max_tokens=2500,
    )
    return _parse_json(raw)


async def run_summarization(
    user_id: str,
    paper_ids: list[str],
    target_words: int = 500,
    verify: bool = True,
) -> dict:
    """
    Summarize one or more papers. For each paper: retrieve chunks section by
    section, classify the paper, draft a type-appropriate summary, then
    fact-check it against the retrieved excerpts.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAPERS)

    async def summarize_paper(paper_id: str) -> dict:
        async with semaphore:
            try:
                chunks = await _retrieve_chunks(user_id, paper_id)

                if not chunks:
                    return {
                        "paper_id": paper_id,
                        "title": "Unknown",
                        "summary": "No content found for this paper. It may not be indexed yet.",
                        "status": "empty",
                    }

                context = _build_context(chunks)
                profile = await _extract_profile(context)

                title = (
                    next((c["title"] for c in chunks if c.get("title")), None)
                    or profile.get("title")
                    or "Untitled Paper"
                )

                draft = await _draft_summary(title, profile, context, target_words)

                summary_text = draft
                issues = []
                verified = False
                if verify:
                    result = await _verify_summary(draft, context)
                    corrected = result.get("corrected_summary")
                    if corrected:
                        summary_text = corrected
                        issues = result.get("issues") or []
                        verified = True

                return {
                    "paper_id": paper_id,
                    "title": title,
                    "authors": profile.get("authors") or [],
                    "year": profile.get("year"),
                    "paper_type": profile.get("paper_type") or "other",
                    "summary": summary_text,
                    "verified": verified,
                    "issues_found": issues,
                    "sources": [
                        {
                            "excerpt": f"E{i + 1}",
                            "page": c.get("page"),
                            "chunk_id": c.get("chunk_id"),
                        }
                        for i, c in enumerate(chunks)
                    ],
                    "chunks_used": len(chunks),
                    "status": "completed",
                }
            except Exception as exc:  # one bad paper must not sink the batch
                return {
                    "paper_id": paper_id,
                    "title": "Unknown",
                    "summary": "",
                    "status": "error",
                    "error": str(exc),
                }

    summaries = await asyncio.gather(*(summarize_paper(pid) for pid in paper_ids))

    return {
        "agent": "summarization",
        "summaries": summaries,
        "total_papers": len(paper_ids),
    }