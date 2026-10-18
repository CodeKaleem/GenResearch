# ============================================================
# GenResearch — Literature Review Agent
# Generates comparative literature reviews from multiple papers
# ============================================================
import asyncio
import hashlib
import json
import re

from services.citation_formatting import (
    CITATION_TAG,
    drop_unknown_citation_tags,
    find_unsupported_numbers,
    flag_uncited_sentences,
    normalize_citation_tags,
    resolve_and_append_references,
)
from database.supabase_client import get_supabase
from services.llm_service import call_llm
from services.rag_service import semantic_search


TOP_K_PER_QUERY = 4
MAX_CHUNKS_PER_PAPER = 6       # was 8 — reduced to leave headroom for the prompt
MIN_CHUNKS_PER_PAPER = 3
TOTAL_CHUNK_BUDGET = 40        # was 48
FIRST_PAGE_CHUNKS = 2  # enough for bibliographic metadata without crowding out findings

# Maximum chars we'll send as excerpts. Derived from the heavy model context window:
# context_tokens × 3.5 chars/token − reserved_for_system_and_prompt_template − output_tokens
# 32 768 × 3.5 ≈ 114 000 chars; minus 10 000 for prompts; minus 4 000 output ≈ 100 000.
# We use a conservative 80 000 so there is never a surprise truncation even if tokenisation
# differs from the 3.5 chars/token estimate.
_CONTEXT_CHAR_BUDGET = 80_000

REQUIRED_SECTIONS = (
    "Introduction",
    "Thematic Analysis",
    "Critical Synthesis",
    "Research Gaps",
    "Conclusion",
)
MIN_WORDS = 450
MAX_WORDS = 1400

REVIEW_QUERIES = {
    "overview": "research question objectives problem scope motivation",
    "methods": "methodology study design data collection sample participants measures analysis",
    "findings": "results findings outcomes evidence reported results",
    "limitations": "limitations weaknesses threats to validity constraints",
    "implications": "discussion implications contributions future work recommendations",
    "adoption": "adoption determinants barriers facilitators attitudes perceived benefits costs information policy support",
    "bibliography": "paper title authors publication year journal DOI citation",
}


LITERATURE_REVIEW_SYSTEM = """You are an expert academic literature-review writer. Synthesize the supplied
evidence into a critical, coherent review; do not write a sequence of paper summaries and do not
write a summary of a single paper when several are supplied.

Requirements:
1. Use exactly these five Markdown H2 headings, in this order: Introduction, Thematic Analysis,
   Critical Synthesis, Research Gaps, Conclusion. Add no other top-level sections (no
   "Recommendations", "Final Thoughts", "Key Findings" or "References"). Target 700-1000 words,
   excluding references.
2. Organize the thematic analysis around claims or debates (use ### subheadings per theme), not one
   paragraph per paper.
3. Compare studies directly only after checking that they address the same outcome, unit,
   population, context, and method. When they do not, describe complementary scope, not
   disagreement. Explain reasons only when the excerpts support them.
4. Evaluate evidence quality and limitations (study design, sample, time frame, retrospective vs
   prospective evidence, reliance on authors' interpretation). Distinguish measured findings from
   authors' interpretations and preserve uncertainty and causal restraint. Do not praise sources
   ("compelling", "timely", "important contribution"); assess them.
5. Give every selected source a substantive, evidence-backed contribution; do not drop a paper
   because it does not fit the dominant theme. Treat adoption/behavioral evidence separately
   from production, clinical, or ecological outcomes when the outcomes are not comparable.
6. Keep distinct mechanisms and outcomes distinct. Where sources describe trade-offs, name the
   specific intervention, taxon/metric/population, and the direction of each claim, and never turn
   a risk tied to one strategy into a general effect of the whole approach. (Example: if a yield
   review presents land sparing as an opportunity for biodiversity while noting reduced genetic
   diversity in high-yielding varieties, keep those two points separate.)
7. Derive research gaps from limitations or missing comparisons in this supplied set. Do not
   claim that a gap is new to the whole field unless the evidence establishes that. Do not write
   generic gaps ("more research is needed"); say what specific comparison, population, method or
   outcome is missing.
8. Use ONLY the supplied excerpts. Cite each specific finding, methodological detail, number,
   limitation, comparison, or gap with one or more supplied [CR-...] tags.
9. Never invent citations, authors, years, results, or relationships between studies. If the
   excerpts do not support a point, qualify it or omit it. Do not add recommendations or advice
   that the excerpts do not contain.
10. Name the source study and design beside precise counts or meta-analysis results; if the
    cited study cannot be identified from the evidence, omit the count. Avoid generic conclusions
    such as "complex," "context-specific," or "interdisciplinary" without stating what evidence
    makes them so. Never leave template placeholders or write [CITATION NEEDED].
11. Make the synthesis explain what the evidence collectively means, where it conflicts, and
    what its limits imply for the strength and scope of conclusions.
12. Write plain prose: no bold text, no horizontal rules, no tables, no bullet lists. Do not refer
    to "excerpts", "the provided sources", or tag IDs in the prose; refer to studies by author-year
    only when that metadata is in the source key, otherwise describe them (e.g. "a systematic
    review of adoption factors")."""


# ------------------------------------------------------------
# Metadata helpers
# ------------------------------------------------------------
def _filename_title(title: str, file_name: str) -> bool:
    stem = file_name.rsplit(".", 1)[0].strip().casefold() if file_name else ""
    normalized = title.strip().casefold()
    return bool(
        (stem and normalized == stem)
        or (" " not in normalized and re.search(r"\d", normalized))
    )


def _paper_metadata(chunks: list[dict], paper_id: str, record: dict | None = None) -> dict:
    chunk = next((item for item in chunks if item.get("title")), chunks[0])
    metadata = chunk.get("metadata") or {}
    record = record or {}
    authors = record.get("authors") or metadata.get("authors") or chunk.get("authors", "")
    if isinstance(authors, list):
        authors = ", ".join(str(author) for author in authors if author)
    title = record.get("title") or metadata.get("title") or chunk.get("title") or ""
    file_name = record.get("file_name", "")
    if _filename_title(title, file_name):
        title = ""
    if isinstance(authors, str) and authors.strip().casefold() in {"unknown", "n/a", "none"}:
        authors = ""
    return {
        "id": "CR-" + hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:12].upper(),
        "paper_id": paper_id,
        "title": title,
        "authors": authors if isinstance(authors, str) else "",
        "year": record.get("year") or metadata.get("year") or chunk.get("year"),
        "doi": metadata.get("doi", chunk.get("doi", "")),
        "url": metadata.get("url", chunk.get("url", "")),
        "journal": metadata.get("journal", "") or "",
        "volume": "",
        "issue": "",
        "pages": "",
        "file_name": file_name,
        "evidence_level": "direct",
    }


def _load_paper_records_sync(user_id: str, paper_ids: list[str]) -> dict[str, dict]:
    response = (
        get_supabase()
        .table("papers")
        .select("id,title,authors,year,file_name")
        .eq("user_id", user_id)
        .in_("id", paper_ids)
        .execute()
    )
    return {str(row["id"]): row for row in (response.data or []) if row.get("id")}


async def _load_paper_records(user_id: str, paper_ids: list[str]) -> dict[str, dict]:
    try:
        return await asyncio.to_thread(_load_paper_records_sync, user_id, paper_ids)
    except Exception:
        return {}


def _normalize_metadata_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _metadata_value_is_supported(value: str, evidence: str) -> bool:
    normalized_value = _normalize_metadata_text(value)
    normalized_evidence = _normalize_metadata_text(evidence)
    return bool(normalized_value and normalized_value in normalized_evidence)


def _parse_json_object(response: str) -> dict:
    """Parse a JSON object out of an LLM response; return {} on any failure."""
    try:
        start, end = response.index("{"), response.rindex("}") + 1
        parsed = json.loads(response[start:end])
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, json.JSONDecodeError, AttributeError):
        return {}


# Backwards-compatible alias for older callers.
_parse_verification = _parse_json_object


def _bibliography_complete(source: dict) -> bool:
    return bool(
        source.get("title") and source.get("authors") and source.get("year")
        and (source.get("journal") or source.get("doi"))
    )


async def _extract_missing_bibliography(
    citation_registry: list[dict], all_chunks: list[dict]
) -> None:
    evidence_by_source = {
        source["id"]: "\n".join(
            chunk.get("text", "")
            for chunk in all_chunks
            if chunk["citation_id"] == source["id"] and (chunk.get("page") == 1 or not chunk.get("page"))
        )
        for source in citation_registry
    }
    missing = [
        source for source in citation_registry
        if not all((source.get(field) for field in ("title", "authors", "year", "journal")))
    ]
    for source in citation_registry:
        doi_match = re.search(
            r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+",
            evidence_by_source[source["id"]],
            re.IGNORECASE,
        )
        if doi_match and not source.get("doi"):
            source["doi"] = doi_match.group(0).rstrip(".,;:)").lower()

    if missing:
        prompt = f"""Extract bibliographic metadata only when it is explicitly printed in the supplied
first-page excerpts. Do not use outside knowledge or infer missing fields. Return JSON only:
{{"sources": [{{"id": "CR-...", "title": null, "authors": [], "year": null,
"journal": null, "volume": null, "issue": null, "pages": null}}]}}
Keep title, author names, and journal wording as printed. Include one object for each source.

--- FIRST-PAGE EVIDENCE ---
{chr(10).join(f"SOURCE {source['id']}\n{evidence_by_source[source['id']]}" for source in missing)}
--- END EVIDENCE ---"""
        try:
            raw = await call_llm(
                prompt=prompt,
                agent_role="literature_review",
                system="Extract only verbatim bibliographic facts. Return valid JSON only.",
                temperature=0.0,
                max_tokens=1800,
            )
        except Exception:
            raw = ""
        parsed = _parse_json_object(raw)
        extracted = {
            item.get("id"): item
            for item in (parsed.get("sources") or [])
            if isinstance(item, dict) and item.get("id")
        }
        for source in missing:
            item = extracted.get(source["id"], {})
            evidence = evidence_by_source[source["id"]]
            title = item.get("title")
            if not source.get("title") and isinstance(title, str) and _metadata_value_is_supported(title, evidence):
                source["title"] = title.strip()
            authors = item.get("authors")
            if not source.get("authors") and isinstance(authors, list) and authors:
                names = [str(name).strip() for name in authors if str(name).strip()]
                evidence_words = set(re.findall(r"[^\W\d_]+", evidence.casefold()))
                if names and all(
                    name.split() and name.split()[-1].casefold().rstrip(".,") in evidence_words
                    for name in names
                ):
                    source["authors"] = ", ".join(names)
            year = str(item.get("year") or "")
            if not source.get("year") and re.fullmatch(r"(?:18|19|20|21)\d{2}", year) and year in evidence:
                source["year"] = int(year)
            for field in ("journal", "volume", "issue", "pages"):
                value = item.get(field)
                if value and not source.get(field) and _metadata_value_is_supported(str(value), evidence):
                    source[field] = str(value).strip()

    for source in citation_registry:
        source["bibliography_complete"] = _bibliography_complete(source)


def _apply_title_fallbacks(citation_registry: list[dict]) -> None:
    """Keep sources whose title could not be read in the reference list, clearly marked.

    Run only AFTER generation so the model never sees (or cites) a filename as a title.
    """
    for source in citation_registry:
        source["title_verified"] = bool(source.get("title"))
        if not source.get("title"):
            stem = (source.get("file_name") or "").rsplit(".", 1)[0].strip()
            source["title"] = stem or "Untitled source"
            source["evidence_level"] = "partial"


# ------------------------------------------------------------
# Retrieval
# ------------------------------------------------------------
def _chunks_per_paper(paper_count: int) -> int:
    return max(MIN_CHUNKS_PER_PAPER, min(MAX_CHUNKS_PER_PAPER, TOTAL_CHUNK_BUDGET // max(paper_count, 1)))


def _chunk_key(chunk: dict) -> str:
    return str(
        chunk.get("chunk_id")
        or chunk.get("id")
        or hashlib.sha1(chunk.get("text", "").encode("utf-8")).hexdigest()
    )


async def _retrieve_paper_chunks(
    user_id: str,
    paper_id: str,
    focus_topic: str,
    max_chunks: int = MAX_CHUNKS_PER_PAPER,
) -> list[dict]:
    queries = [
        f"{focus_topic} {query}".strip() if focus_topic else query
        for query in REVIEW_QUERIES.values()
    ]
    results = await asyncio.gather(
        *(
            semantic_search(
                user_id=user_id,
                query=query,
                top_k=TOP_K_PER_QUERY,
                paper_id=paper_id,
            )
            for query in queries
        ),
        return_exceptions=True,
    )

    query_groups: list[list[dict]] = []
    for result in results:
        if isinstance(result, Exception):
            query_groups.append([])
            continue
        query_groups.append(list(result or []))

    def relevance(chunk: dict) -> float:
        if chunk.get("hybrid_score") is not None:
            return float(chunk["hybrid_score"])
        return -float(chunk.get("distance", 1.0))

    for group in query_groups:
        group.sort(key=relevance, reverse=True)

    selected: list[dict] = []
    seen: set[str] = set()

    def add_chunk(chunk: dict) -> None:
        key = _chunk_key(chunk)
        if key not in seen and len(selected) < max_chunks:
            seen.add(key)
            selected.append(chunk)

    first_page_chunks = {
        _chunk_key(chunk): chunk
        for group in query_groups
        for chunk in group
        if chunk.get("page") == 1
    }
    for chunk in list(first_page_chunks.values())[:FIRST_PAGE_CHUNKS]:
        add_chunk(chunk)

    for rank in range(TOP_K_PER_QUERY):
        for group in query_groups:
            if rank < len(group):
                add_chunk(group[rank])
            if len(selected) >= max_chunks:
                break
        if len(selected) >= max_chunks:
            break
    return selected


# ------------------------------------------------------------
# Review text normalisation + validation
# ------------------------------------------------------------
_SECTION_NAMES = {name.casefold(): name for name in REQUIRED_SECTIONS}
_SECTION_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:\d+[.)]\s*)?"
    r"(Introduction|Thematic Analysis|Critical Synthesis|Research Gaps|Conclusion)"
    r"\s*(?:\*\*|__)?\s*:?\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE,
)
_RULE_LINE = re.compile(r"^\s*(?:[-*_]\s*){3,}$")
_REFERENCES_HEADING = re.compile(
    r"^\s*#{1,6}\s*\**\s*(?:references|bibliography|works cited)\b", re.IGNORECASE
)
_MODEL_MARKER = re.compile(r"[ \t]*\[CITATION NEEDED\]")


def _normalize_review_markup(text: str) -> str:
    """Clean model output: canonical H2 headings, no rules/markers/self-written references."""
    text = (text or "").replace("\r\n", "\n").strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)

    lines: list[str] = []
    for line in text.split("\n"):
        if _REFERENCES_HEADING.match(line):
            break  # the reference list is generated from the registry
        if _RULE_LINE.match(line):
            continue
        section = _SECTION_LINE.match(line)
        if section:
            lines.append(f"## {_SECTION_NAMES[section.group(1).casefold()]}")
            continue
        lines.append(line)

    text = "\n".join(lines)
    text = _MODEL_MARKER.sub("", text)
    text = normalize_citation_tags(text)
    text = re.sub(r"(?m)^(#{1,6} .+)$", r"\n\1\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _review_problems(text: str, registry: list[dict]) -> list[str]:
    """Structural and coverage problems that justify a repair pass."""
    problems: list[str] = []
    headings = re.findall(r"(?m)^##\s+(.+?)\s*$", text)
    present = {heading.casefold() for heading in headings}

    missing = [name for name in REQUIRED_SECTIONS if name.casefold() not in present]
    if missing:
        problems.append("Missing required section heading(s): " + ", ".join(missing) + ".")
    extra = [heading for heading in headings if heading.casefold() not in _SECTION_NAMES]
    if extra:
        problems.append(
            "Remove unexpected top-level section(s): " + ", ".join(extra)
            + ". Use only the five required headings."
        )

    valid = {source["id"] for source in registry}
    cited = {item.upper() for item in CITATION_TAG.findall(text)}
    if not cited & valid:
        problems.append("No valid [CR-...] citation tags were found; cite every substantive sentence.")
    unknown = cited - valid
    if unknown:
        problems.append("Unknown citation tags used: " + ", ".join(sorted(unknown)) + ".")
    uncited = [source for source in registry if source["id"] not in cited]
    if uncited:
        problems.append(
            "These sources are never cited; give each a substantive, correctly cited point: "
            + "; ".join(f"{s['id']} ({s.get('title') or 'title not verified'})" for s in uncited)
            + "."
        )

    words = len(re.findall(r"\b\w+\b", CITATION_TAG.sub("", text)))
    if words < MIN_WORDS:
        problems.append(f"Too short ({words} words); target 700-1000 words.")
    elif words > MAX_WORDS:
        problems.append(f"Too long ({words} words); target 700-1000 words.")
    return problems


# ------------------------------------------------------------
# Prompt builders
# ------------------------------------------------------------
def _source_key(registry: list[dict]) -> str:
    return "\n".join(
        f"- {item['id']}: {item['title'] or 'Title not verified'} | "
        f"{item['authors'] or 'Author unknown'} | {item['year'] or 'Year unknown'}"
        for item in registry
    )


def _trim_context_to_budget(
    registry: list[dict],
    all_chunks: list[dict],
    char_budget: int = _CONTEXT_CHAR_BUDGET,
) -> list[dict]:
    """Return a trimmed copy of all_chunks that fits within char_budget.

    Strategy:
    - Each source is guaranteed at least 1 chunk (so every paper can be cited).
    - Beyond that minimum, chunks are kept in their natural order (best-relevance
      first, since retrieval sorted them) until the budget is exhausted.
    - The SOURCE header text (~120 chars each) is counted against the budget too.
    """
    # Guarantee floor: 1 chunk per source
    by_source: dict[str, list[dict]] = {s["id"]: [] for s in registry}
    for chunk in all_chunks:
        cid = chunk.get("citation_id", "")
        if cid in by_source:
            by_source[cid].append(chunk)

    header_overhead = len(registry) * 120  # rough chars for === SOURCE ... === lines
    remaining = char_budget - header_overhead
    selected: list[dict] = []

    # First pass: guaranteed floor (1 chunk per source)
    for source in registry:
        chunks = by_source[source["id"]]
        if chunks:
            chosen = chunks[0]
            selected.append(chosen)
            remaining -= len(chosen.get("text", ""))

    # Second pass: fill the rest of the budget with remaining chunks
    for source in registry:
        chunks = by_source[source["id"]][1:]  # skip the already-selected floor chunk
        for chunk in chunks:
            size = len(chunk.get("text", ""))
            if remaining - size < 0:
                break
            selected.append(chunk)
            remaining -= size

    # Preserve original order
    order = {_chunk_key(c): i for i, c in enumerate(all_chunks)}
    selected.sort(key=lambda c: order.get(_chunk_key(c), 9999))
    return selected


def _build_context(registry: list[dict], all_chunks: list[dict]) -> str:
    """Group excerpts by source so the model can see every paper is present.

    Trims the chunk list to _CONTEXT_CHAR_BUDGET before building the string so
    the resulting prompt never overflows the model's context window.
    """
    trimmed = _trim_context_to_budget(registry, all_chunks)
    blocks = []
    for source in registry:
        header = (
            f"=== SOURCE {source['id']} | {source['title'] or 'Title not verified'} | "
            f"{source['authors'] or 'Author unknown'} | {source['year'] or 'Year unknown'} ==="
        )
        body = "\n\n".join(
            f"[{source['id']} | page {chunk.get('page') or 'unknown'}]\n{chunk.get('text', '')}"
            for chunk in trimmed
            if chunk["citation_id"] == source["id"]
        )
        blocks.append(f"{header}\n\n{body}")
    return "\n\n".join(blocks)



def _build_generation_prompt(
    registry: list[dict], context: str, focus_topic: str
) -> str:
    topic_instruction = (
        f'Focus the review on the topic: "{focus_topic}".'
        if focus_topic
        else "Identify the central themes and debates represented in the supplied papers."
    )
    comparison_instruction = (
        "Compare only like with like. Before calling findings contradictory, check outcome, "
        "unit, population, context, methods, and time scale; otherwise frame them as "
        "complementary evidence with different scopes."
        if len(registry) > 1
        else "This is a single-paper review: critically synthesize its evidence and do not imply cross-study comparisons."
    )
    example_tag = f"[{registry[0]['id']}]"
    checklist = "\n".join(f"- [{item['id']}]" for item in registry)

    return f"""Write a critical literature review grounded ONLY in the excerpts below.

SOURCE KEY (cite using these exact tags; never cite filenames):
{_source_key(registry)}

{topic_instruction}
{comparison_instruction}

REQUIRED FORMAT
- Exactly these five H2 headings, in this order: ## Introduction, ## Thematic Analysis, ## Critical Synthesis, ## Research Gaps, ## Conclusion.
- Rough length: Introduction 100-150 words; Thematic Analysis 350-450 words (### subheadings per theme or debate, never per paper); Critical Synthesis 150-250; Research Gaps 100-150; Conclusion 80-120.
- Plain prose only. No bold, no horizontal rules, no tables, no lists, no reference list, no extra sections.
- Place citation tags immediately before the sentence's final punctuation, for example: "...was reported in the trial {example_tag}." For several sources use [CR-A][CR-B].
- Never write [CITATION NEEDED].

COVERAGE CHECKLIST: every tag below must be cited at least once with a substantive, evidence-based point
(a review that rests on only some of the papers is a failure):
{checklist}

PLAN SILENTLY BEFORE WRITING (do not output the plan): which excerpts support each theme; where sources
genuinely agree or conflict (same outcome, population, method?); methodological differences; limitations;
and which gaps follow from this supplied set. A disagreement must compare the same outcome and population;
distinct domains (for example livestock vs crop outcomes, or retrospective benchmarks vs prospective
validation) are complementary, not contradictory, unless the studies measure a shared outcome. Every
comparison must be supported by citations to both studies. Name the source study and design beside any
precise count or meta-analysis result. Use author-year prose only when metadata is present in the source key.

--- PAPER EXCERPTS (grouped by source) ---

{context}

--- END OF EXCERPTS ---

Write the review now:"""


def _build_repair_prompt(
    registry: list[dict], context: str, draft: str, problems: list[str]
) -> str:
    return f"""Revise the draft literature review so that every listed problem is fixed.

PROBLEMS TO FIX:
{chr(10).join(f"- {problem}" for problem in problems)}

SOURCE KEY:
{_source_key(registry)}

Rules: use exactly the five H2 headings (Introduction, Thematic Analysis, Critical Synthesis, Research Gaps,
Conclusion) in that order; plain prose with ### subheadings only inside Thematic Analysis; 700-1000 words;
use ONLY the excerpts below; cite every substantive sentence with the exact [CR-...] tags from the source key
(tag immediately before the final punctuation); every source must receive at least one substantive cited
point; compare studies only when they measure the same outcome and population; no praise, no recommendations
that the excerpts do not contain, no reference list, never write [CITATION NEEDED]. Keep supported content
from the draft; remove or qualify anything the excerpts do not support.

--- SOURCE EXCERPTS ---
{context}
--- END SOURCE EXCERPTS ---

--- DRAFT ---
{draft}
--- END DRAFT ---

Return ONLY the revised review in Markdown:"""


def _build_audit_prompt(context: str, draft: str) -> str:
    return f"""Audit the draft against the source excerpts. Check whether every selected paper contributes
at least one substantive, correctly cited point; whether every specific claim, number, comparison, limitation
and proposed gap is supported by the cited source(s); whether contradictions and uncertainty are represented
fairly; and whether the draft synthesizes rather than lists papers. Do not describe differences between
non-comparable outcomes (for example livestock vs crop outcomes) as contradictory findings, and do not merge
distinct risks and opportunities. Remove or qualify unsupported claims; never add facts; never drop a source;
keep the same five H2 headings and the valid [CR-...] citation tags; do not add sections or a reference list.
If no correction is needed, return the draft unchanged.

Reply in EXACTLY this format and nothing else:

ISSUES:
- one concise issue per line (write "- none" if there are no issues)

CORRECTED_REVIEW:
<the full corrected review in Markdown>

--- SOURCE EXCERPTS ---
{context}
--- END SOURCE EXCERPTS ---

--- DRAFT ---
{draft}
--- END DRAFT ---"""


_AUDIT_FORMAT = re.compile(r"ISSUES:\s*(.*?)\s*CORRECTED_REVIEW:\s*(.*)\Z", re.DOTALL | re.IGNORECASE)


def _parse_audit(response: str) -> dict:
    """Parse the auditor's reply (delimited format preferred, JSON accepted)."""
    if not response:
        return {}
    match = _AUDIT_FORMAT.search(response)
    if match:
        issues = [
            re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            for line in match.group(1).splitlines()
            if line.strip()
        ]
        issues = [item for item in issues if item.casefold().rstrip(".") != "none"]
        return {"issues": issues, "corrected_review": match.group(2).strip()}
    parsed = _parse_json_object(response)
    if parsed:
        issues = parsed.get("issues")
        parsed["issues"] = [str(item) for item in issues] if isinstance(issues, list) else []
    return parsed


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------
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
    citation_registry: list[dict] = []
    paper_titles: list[str] = []
    unique_paper_ids = list(dict.fromkeys(paper_ids))
    paper_records = await _load_paper_records(user_id, unique_paper_ids)

    per_paper = _chunks_per_paper(len(unique_paper_ids))
    retrieved = await asyncio.gather(
        *(
            _retrieve_paper_chunks(user_id, paper_id, focus_topic, per_paper)
            for paper_id in unique_paper_ids
        )
    )
    for paper_id, chunks in zip(unique_paper_ids, retrieved):
        if not chunks:
            continue
        source = _paper_metadata(chunks, paper_id, paper_records.get(paper_id))
        citation_registry.append(source)
        paper_titles.append(source["title"] or "Title not verified")
        for chunk in chunks:
            all_chunks.append({**chunk, "citation_id": source["id"]})

    if not citation_registry:
        return {
            "agent": "literature_review",
            "review": "No content found in the selected papers.",
            "papers_analyzed": 0,
            "status": "empty",
        }

    await _extract_missing_bibliography(citation_registry, all_chunks)

    valid_ids = {source["id"] for source in citation_registry}
    evidence_by_source = {
        source["id"]: "\n".join(
            chunk.get("text", "") for chunk in all_chunks if chunk["citation_id"] == source["id"]
        )
        for source in citation_registry
    }
    context = _build_context(citation_registry, all_chunks)

    # ---- 1. Draft ----------------------------------------------------------
    try:
        draft = await call_llm(
            prompt=_build_generation_prompt(citation_registry, context, focus_topic),
            agent_role="literature_review",
            system=LITERATURE_REVIEW_SYSTEM,
            temperature=0.2,
            max_tokens=4000,
        )
    except Exception as exc:
        return {
            "agent": "literature_review",
            "review": f"The review could not be generated: {exc}",
            "papers_analyzed": len(paper_titles),
            "paper_titles": paper_titles,
            "sources": citation_registry,
            "status": "error",
        }

    candidate = _normalize_review_markup(draft)
    problems = _review_problems(candidate, citation_registry)

    # ---- 2. Structural repair (one targeted retry) -------------------------
    repair_attempted = False
    if problems:
        repair_attempted = True
        try:
            repaired_raw = await call_llm(
                prompt=_build_repair_prompt(citation_registry, context, candidate, problems),
                agent_role="literature_review",
                system=LITERATURE_REVIEW_SYSTEM,
                temperature=0.1,
                max_tokens=4000,
            )
        except Exception:
            repaired_raw = ""
        repaired = _normalize_review_markup(repaired_raw)
        if repaired:
            repaired_problems = _review_problems(repaired, citation_registry)
            if len(repaired_problems) <= len(problems):
                candidate, problems = repaired, repaired_problems

    # ---- 3. Evidence audit ---------------------------------------------------
    audit_issues: list[str] = []
    audit_accepted = False
    try:
        audit_raw = await call_llm(
            prompt=_build_audit_prompt(context, candidate),
            agent_role="literature_review",
            system="You are a strict academic evidence auditor. Follow the requested output format exactly.",
            temperature=0.0,
            max_tokens=4500,
        )
    except Exception:
        audit_raw = ""
    audit = _parse_audit(audit_raw)
    audit_issues = [str(item) for item in (audit.get("issues") or [])]
    corrected = audit.get("corrected_review")
    if isinstance(corrected, str) and corrected.strip():
        corrected = _normalize_review_markup(corrected)
        corrected_problems = _review_problems(corrected, citation_registry)
        if corrected and len(corrected_problems) <= len(problems):
            candidate, problems, audit_accepted = corrected, corrected_problems, True
        else:
            audit_issues.append(
                "The auditor's rewrite was discarded because it broke the required structure or dropped sources."
            )
    if not audit_accepted and not audit_issues:
        audit_issues.append("Evidence audit unavailable; draft was not independently verified.")

    # ---- 4. Post-processing --------------------------------------------------
    review_text = drop_unknown_citation_tags(candidate, valid_ids)
    number_warnings = find_unsupported_numbers(
        review_text,
        evidence_by_source,
        valid_ids,
        extra_allowed=_source_key(citation_registry),
    )

    cited_source_ids = {item.upper() for item in CITATION_TAG.findall(review_text)}
    uncited_sources = [
        {"id": source["id"], "title": source.get("title") or "Title not verified"}
        for source in citation_registry
        if source["id"] not in cited_source_ids
    ]

    _apply_title_fallbacks(citation_registry)
    # Resolve [CR-...] tags to author-year text BEFORE the uncited-sentence check.
    # If we flag first, the [CR-...] tags are still present and valid sentences pass
    # the check — but the old code was already correct in that regard.  The critical
    # fix here is that resolve_and_append_references now runs with freeform-citation
    # checking AFTER tag resolution, eliminating the double-flagging that produced
    # "[CITATION NEEDED]" next to "(Baudry et al., 2018)" in the final output.
    review_text = resolve_and_append_references(review_text, citation_registry)
    review_text, uncited_count, sentence_count = flag_uncited_sentences(review_text, valid_ids)


    return {
        "agent": "literature_review",
        "review": review_text,
        "papers_analyzed": len(paper_titles),
        "paper_titles": paper_titles,
        "chunks_used": len(all_chunks),
        "focus_topic": focus_topic,
        "sources": citation_registry,
        "bibliography_quality": {
            "complete_sources": sum(bool(source.get("bibliography_complete")) for source in citation_registry),
            "total_sources": len(citation_registry),
        },
        "verification": {
            "completed": audit_accepted,
            "issues": audit_issues,
        },
        "structure": {
            "repair_attempted": repair_attempted,
            "remaining_problems": problems,
        },
        "warnings": number_warnings,
        "citation_quality": {
            "coverage": round((sentence_count - uncited_count) / sentence_count, 3)
            if sentence_count
            else 1.0,
            "uncited_sentences": uncited_count,
            "sentences_checked": sentence_count,
            "sources_cited": len(citation_registry) - len(uncited_sources),
            "sources_uncited": uncited_sources,
        },
        "status": "completed",
    }