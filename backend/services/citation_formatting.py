# ============================================================
# GenResearch — Citation Formatting
# Resolves internal [CR-001] registry tags into proper in-text
# citations, and builds a properly formatted, alphabetized
# reference list.
# ============================================================
from __future__ import annotations

import re
from dataclasses import dataclass

from services.text_utils import split_sentences

CITATION_TAG = re.compile(r"\[(CR-\d{3})\]")
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[,.]\d+)*(?:\s?%|\s+percent)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ENTITY = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z][a-z]+[A-Z][A-Za-z0-9]*|"
    r"[A-Z]{2,}[A-Z0-9-]*|[A-Z][A-Z0-9-]*\d[A-Z0-9-]*)\b"
)
_DUPLICATE_CITATION_NEEDED = re.compile(
    r"\[CITATION NEEDED\](?:\s*\[CITATION NEEDED\])+"
)

_FREEFORM_CITATION = re.compile(
    r"\(\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+"
    r"(?:\s+et\s+al\.?|\s*(?:,|&|and)\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+)?"
    r",\s*\d{4}[a-z]?\s*\)"
)


def flag_unverified_freeform_citations(text: str) -> str:
    """Replace author/year citations that cannot be checked against the registry."""
    return _FREEFORM_CITATION.sub("[CITATION NEEDED]", text)


def collapse_duplicate_citation_markers(text: str) -> str:
    """Collapse adjacent repeated citation-needed markers into one."""
    return _DUPLICATE_CITATION_NEEDED.sub("[CITATION NEEDED]", text)


def _split_sentences(text: str) -> list[str]:
    """Compatibility wrapper for callers of the original formatter helper."""
    return split_sentences(text)


# Catches placeholder-template syntax the draft agent copies literally
# instead of filling in — e.g. "[Author A, Year] [CR-00X]" lifted straight
# from a prompt exemplar. Two patterns:
#   - "[Author <Letter>, Year]"-shaped brackets (never a real citation)
#   - "[CR-...]"-shaped brackets that aren't a real 3-digit ID (a near-miss
#     like [CR-00X] reads as a real tag to someone skimming, but CITATION_TAG
#     requires exactly 3 digits and silently ignores anything else)
_PLACEHOLDER_AUTHOR_BRACKET = re.compile(r"\[\s*Author\s+[A-Za-z]\s*,?\s*Year\s*\]", re.IGNORECASE)
_NEAR_MISS_CR_TAG = re.compile(r"\[CR-(?!\d{3})[^\]]*\]")


def flag_placeholder_template_syntax(text: str) -> str:
    """Replace copied-literally exemplar placeholder syntax with an honest flag."""
    text = _PLACEHOLDER_AUTHOR_BRACKET.sub("[CITATION NEEDED]", text)
    text = _NEAR_MISS_CR_TAG.sub("[CITATION NEEDED]", text)
    return text


def _normalize_grounding_text(text: str) -> str:
    return " ".join(re.findall(r"\d+(?:[,.]\d+)*%|[a-z0-9]+", text.lower()))


_CITING_AUTHOR_PHRASE = re.compile(
    r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+)?\s+et al\.?",
)
_SINGLE_CAPITALIZED_ENTITY = re.compile(r"\b[A-Z][a-z][A-Za-z0-9-]{3,}\b")
_TERMINAL_PUNCTUATION = re.compile(r"([.!?]+[\"'’”\)\]]*)$")
_TRAILING_MARKER = re.compile(r"([.!?])\s+(\[CITATION NEEDED\])(?=\s|$)")


@dataclass(frozen=True)
class GroundingResult:
    text: str
    removed_claims: list[str]
    flagged_count: int
    sentence_count: int
    preserved_empty_section: bool = False


def _entity_candidates(body: str) -> list[str]:
    body = body.replace("[CITATION NEEDED]", "")
    body = _CITING_AUTHOR_PHRASE.sub("", body)
    first_word = re.search(r"\S+", body)
    sentence_start = first_word.start() if first_word else -1
    candidates = [
        match.group(0)
        for match in _ENTITY.finditer(body)
        if match.start() != sentence_start
    ]
    candidates.extend(
        match.group(0)
        for match in _SINGLE_CAPITALIZED_ENTITY.finditer(body)
        if match.start() != sentence_start
    )
    return candidates


def _mark_before_terminal_punctuation(sentence: str) -> str:
    sentence = re.sub(r"\s*\[CITATION NEEDED\]", "", sentence).rstrip()
    match = _TERMINAL_PUNCTUATION.search(sentence)
    if not match:
        return f"{sentence.rstrip()} [CITATION NEEDED]"
    body = sentence[:match.start()].rstrip()
    return f"{body} [CITATION NEEDED]{match.group(1)}"


def ground_ungrounded_specifics(
    text: str,
    evidence_by_source: dict[str, str],
    valid_source_ids: set[str],
    topic: str = "",
) -> GroundingResult:
    """Flag generic uncited prose and remove unsupported specifics lacking a valid source."""
    text = _TRAILING_MARKER.sub(r" \2\1", text)
    sentences = [sentence.strip() for sentence in split_sentences(text) if sentence.strip()]
    checked_sentences: list[str] = []
    removed_claims: list[str] = []
    flagged_count = 0

    for sentence in sentences:
        citation_ids = set(CITATION_TAG.findall(sentence))
        valid_ids = citation_ids & valid_source_ids
        body = CITATION_TAG.sub("", sentence)
        evidence = " ".join(evidence_by_source.get(cid, "") for cid in valid_ids)
        allowed = _normalize_grounding_text(f"{evidence} {topic}")
        specifics = _NUMBER.findall(body) + _entity_candidates(body)
        unsupported_specifics = [
            specific
            for specific in dict.fromkeys(specifics)
            if _normalize_grounding_text(specific) not in allowed
        ]
        needs_flag = (
            not valid_ids
            or bool(citation_ids - valid_source_ids)
            or bool(unsupported_specifics)
        )

        if unsupported_specifics and not valid_ids:
            removed_claims.append(sentence)
            flagged_count += 1
            continue
        if needs_flag:
            sentence = _mark_before_terminal_punctuation(sentence)
            flagged_count += 1
        checked_sentences.append(sentence)

    preserved_empty = bool(sentences and not checked_sentences and removed_claims)
    if preserved_empty:
        checked_sentences = sentences
        removed_claims = []

    return GroundingResult(
        text=collapse_duplicate_citation_markers(" ".join(checked_sentences)),
        removed_claims=removed_claims,
        flagged_count=flagged_count,
        sentence_count=len(sentences),
        preserved_empty_section=preserved_empty,
    )


def flag_ungrounded_specifics(
    text: str,
    evidence_by_source: dict[str, str],
    valid_source_ids: set[str],
    topic: str = "",
) -> str:
    """Flag sentences without valid citations or with unsupported specifics."""
    return ground_ungrounded_specifics(
        text, evidence_by_source, valid_source_ids, topic
    ).text

# Matches common academic author-list formats: "Surname, F. M." units,
# e.g. "Tay, Y., Dehghani, M., Bahri, D.".
_AUTHOR_UNIT = re.compile(r"([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+),\s*((?:[A-Z]\.\s*)+)")


def _split_authors(authors: str) -> list[str]:
    """Best-effort split of a free-text author string into individual names."""
    if not authors or authors.strip().lower() == "unknown":
        return []

    normalized = re.sub(r"\s*(?:&|;)\s*|\s+and\s+", ", ", authors)

    units = _AUTHOR_UNIT.findall(normalized)
    if units:
        return [f"{surname}, {initials.strip()}" for surname, initials in units]

    # If no "Surname, F." pattern is detected, assume a comma-separated list.
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _surname(name: str) -> str:
    """Pull a surname out of 'Last, F.' or 'First Last' formats."""
    name = name.strip()
    if "," in name:
        return name.split(",", 1)[0].strip()
    tokens = name.split()
    return tokens[-1] if tokens else name


def format_in_text_citation(entry: dict) -> str:
    """Render one registry entry as an APA-style parenthetical citation."""
    year = entry.get("year") or "n.d."
    authors = _split_authors(entry.get("authors", ""))

    if not authors:
        title = entry.get("title", "Untitled").strip()
        short_title = title if len(title) <= 40 else title[:37].rstrip() + "..."
        return f'("{short_title}", {year})'

    if len(authors) == 1:
        return f"({_surname(authors[0])}, {year})"
    if len(authors) == 2:
        return f"({_surname(authors[0])} & {_surname(authors[1])}, {year})"
    return f"({_surname(authors[0])} et al., {year})"


def resolve_in_text_citations(text: str, citation_registry: list[dict]) -> str:
    """Replace every [CR-XXX] tag with a proper in-text citation."""
    registry = {
        entry.get("id"): entry
        for entry in citation_registry
        if entry.get("evidence_level") != "none"
    }

    def replace_tag(match: re.Match) -> str:
        entry = registry.get(match.group(1))
        return format_in_text_citation(entry) if entry else "(citation needed)"

    return CITATION_TAG.sub(replace_tag, text)


def format_apa_reference(entry: dict) -> str:
    """Format one registry entry as an APA-style reference-list entry."""
    authors_list = _split_authors(entry.get("authors", "Unknown"))
    if authors_list:
        authors = ", ".join(authors_list[:-1])
        authors = f"{authors}, & {authors_list[-1]}" if len(authors_list) > 1 else authors_list[0]
    else:
        authors = ""

    year = entry.get("year") or "n.d."
    title = entry.get("title", "Untitled").strip().rstrip(".")
    doi = (entry.get("doi") or "").strip()
    url = (entry.get("url") or "").strip()

    pieces = []
    if authors:
        pieces.append(f"{authors} ({year}).")
    else:
        pieces.append(f"{title} ({year}).")
        title = ""
    if title:
        pieces.append(f"{title}.")
    if doi:
        pieces.append(doi if doi.startswith("http") else f"https://doi.org/{doi}")
    elif url:
        pieces.append(url)

    return " ".join(piece for piece in pieces if piece)


def build_reference_list(
    citation_registry: list[dict], used_ids: set[str] | None = None
) -> list[str]:
    """Build an alphabetized reference list, optionally limited to used IDs."""
    entries = citation_registry
    if used_ids is not None:
        entries = [entry for entry in entries if entry.get("id") in used_ids]
    entries = [entry for entry in entries if entry.get("evidence_level") != "none"]

    def sort_key(entry: dict) -> str:
        authors = _split_authors(entry.get("authors", ""))
        return _surname(authors[0]).lower() if authors else entry.get("title", "").lower()

    return [format_apa_reference(entry) for entry in sorted(entries, key=sort_key)]


def resolve_and_append_references(
    draft_text: str,
    citation_registry: list[dict],
    heading: str = "## References",
) -> str:
    """Resolve in-text citation tags and append references for cited sources."""
    if (
        not CITATION_TAG.search(draft_text)
        and re.search(r"(?im)^\s*##\s+references\s*$", draft_text)
    ):
        return draft_text

    draft_text = flag_placeholder_template_syntax(draft_text)
    draft_text = flag_unverified_freeform_citations(draft_text)
    draft_text = collapse_duplicate_citation_markers(draft_text)
    used_ids = set(CITATION_TAG.findall(draft_text))
    resolved = resolve_in_text_citations(draft_text, citation_registry)
    references = build_reference_list(citation_registry, used_ids=used_ids)

    if not references:
        return resolved

    reference_block = "\n".join(references)
    return f"{resolved}\n\n{heading}\n\n{reference_block}"
