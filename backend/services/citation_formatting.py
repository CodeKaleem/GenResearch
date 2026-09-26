# ============================================================
# GenResearch — Citation Formatting
# Resolves internal [CR-001] registry tags into proper in-text
# citations, and builds a properly formatted, alphabetized
# reference list.
# ============================================================
from __future__ import annotations

import re

CITATION_TAG = re.compile(r"\[(CR-\d{3})\]")

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
    registry = {entry.get("id"): entry for entry in citation_registry}

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
    used_ids = set(CITATION_TAG.findall(draft_text))
    resolved = resolve_in_text_citations(draft_text, citation_registry)
    references = build_reference_list(citation_registry, used_ids=used_ids)

    if not references:
        return resolved

    reference_block = "\n".join(references)
    return f"{resolved}\n\n{heading}\n\n{reference_block}"
