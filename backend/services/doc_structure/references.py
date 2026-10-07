from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

_HEADING_RE = re.compile(r"(?:^|\n)\s*(?:References|Bibliography|Works Cited|Literature Cited|REFERENCES)\s*$", re.IGNORECASE)
_REFERENCE_MARKER_RE = re.compile(r"(?m)^\s*\[(\d+)\]\s+|")


@dataclass
class ReferenceEntry:
    ref_number: int | None = None
    raw: str = ""
    authors: str | None = None
    title: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    parse_confidence: float = 0.0
    verified: bool = False
    verification_source: str | None = None


@dataclass
class ReferenceBundle:
    entries: list[ReferenceEntry] = field(default_factory=list)
    references_start_page: int | None = None
    reference_count: int = 0
    expected_reference_count: int = 0
    missing_reference_ids: list[int] = field(default_factory=list)


def _normalize_reference_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=[A-Za-z])-\n(?=[a-z])", "", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def _find_reference_heading(text: str) -> tuple[int, str] | None:
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return None
    heading = matches[-1]
    start = heading.end()
    window = text[start:start + 500]
    if not re.search(r"(?i)(\[\s*1\s*\]|\b1\.|\(1\)|[A-Z][a-z]+,\s+[A-Z]\.?\s*[A-Z]?[A-Za-z\-]*\s*\(\d{4}\))", window):
        return None
    return heading.start(), text[start:]


def _extract_ids_from_text(text: str) -> list[int]:
    ids = []
    for match in re.finditer(r"(?<![A-Za-z])\[(\d+)\](?![A-Za-z])", text):
        ids.append(int(match.group(1)))
    for match in re.finditer(r"(?m)^\s*(\d+)\.\s+", text):
        ids.append(int(match.group(1)))
    return ids


def _coerce_year(raw: str) -> int | None:
    match = re.search(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", raw)
    if not match:
        return None
    return int(match.group(1))


def _coerce_doi(raw: str) -> str | None:
    match = re.search(r"10\.\d{4,9}/\S+", raw, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0)


def _coerce_arxiv(raw: str) -> str | None:
    match = re.search(r"arXiv:(\d{4}\.\d{4,5})", raw, flags=re.IGNORECASE)
    if not match:
        return None
    return f"arXiv:{match.group(1)}"


def _strip_ref_noise(raw: str) -> str:
    raw = re.sub(r"(?i)\b(doi|arxiv|url|available at|accessed on).*?$", "", raw)
    return raw.strip(" -•\n")


def _parse_reference_entry(raw: str) -> ReferenceEntry:
    cleaned = _normalize_reference_text(raw)
    entry = ReferenceEntry(raw=cleaned)
    match = re.search(r"^\s*\[(\d+)\]\s*", cleaned)
    if match:
        entry.ref_number = int(match.group(1))
        cleaned = cleaned[match.end():].lstrip()
    entry.year = _coerce_year(cleaned)
    entry.doi = _coerce_doi(cleaned)
    entry.arxiv_id = _coerce_arxiv(cleaned)
    entry.authors = None
    entry.title = None
    title_match = re.search(r"\s+([A-Z][^.;]+(?:\.[^.;]+)*)\.?\s*(?:\.|\b(?:In|Proc\.|Proceedings|Journal|Transactions|Conference|ACM|IEEE|arXiv|doi|URL))", cleaned)
    if title_match:
        entry.title = title_match.group(1).strip(" .")
        entry.authors = cleaned[:title_match.start()].strip(" .")
    if not entry.authors:
        author_bits = re.split(r"\s+(?:[A-Z][^\n]+?\.\s+(?:[A-Z][^\n]+?\.)?)\s+", cleaned, maxsplit=1)
        if len(author_bits) > 1 and author_bits[0]:
            entry.authors = author_bits[0].strip(" .")
    if not entry.title:
        entry.title = re.sub(r"^.*?\s+(?=[A-Z][^\n]+\.)", "", cleaned, count=1)[:200]
    entry.venue = None
    if entry.title:
        rest = cleaned.split(entry.title, 1)[1] if entry.title in cleaned else ""
        if rest:
            venue_candidate = re.sub(r"^\s*[-:;,.\s]+", "", rest)
            entry.venue = venue_candidate[:200].strip(" .") or None
    entry.parse_confidence = 0.5
    if entry.year is not None:
        entry.parse_confidence += 0.2
    if entry.title:
        entry.parse_confidence += 0.2
    if entry.doi or entry.arxiv_id:
        entry.parse_confidence += 0.1
    entry.parse_confidence = min(1.0, entry.parse_confidence)
    return entry


def _split_numbered_entries(text: str) -> list[str]:
    cleaned = _normalize_reference_text(text)
    marker_re = re.compile(r"(?m)^\s*\[(\d+)\]\s+")
    matches = list(marker_re.finditer(cleaned))
    if not matches:
        return []
    entries: list[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        segment = cleaned[start:end].strip()
        if segment:
            entries.append(segment)
    return entries


def _extract_reference_entries_from_text(text: str) -> list[ReferenceEntry]:
    cleaned = _normalize_reference_text(text)
    entries: list[ReferenceEntry] = []
    for segment in _split_numbered_entries(cleaned):
        entry = _parse_reference_entry(segment)
        if entry.raw:
            entries.append(entry)
    if entries:
        return entries

    # Recovery pass for inline markers or glued references
    recovered: list[ReferenceEntry] = []
    for match in re.finditer(r"\[(\d+)\]\s*([^\[]+?)(?=(?:\[(?:\d+)\]|\Z))", cleaned, flags=re.DOTALL):
        raw = match.group(0).strip()
        if raw:
            recovered.append(_parse_reference_entry(raw))
    return recovered


def parse_reference_entries(reference_text: str) -> ReferenceBundle:
    text = _normalize_reference_text(reference_text)
    heading_info = _find_reference_heading(text)
    if heading_info:
        _, reference_body = heading_info
        text = reference_body
    ids: list[int] = []
    entries = _extract_reference_entries_from_text(text)
    for entry in entries:
        if entry.ref_number is not None:
            ids.append(entry.ref_number)
    if not ids:
        ids = _extract_ids_from_text(text)
    expected = max(ids) if ids else 0
    seen = {entry.ref_number for entry in entries if entry.ref_number is not None}
    missing = sorted({n for n in range(1, expected + 1) if n not in seen})
    if expected and not missing and len(entries) < expected:
        missing = sorted(set(range(1, expected + 1)) - {entry.ref_number for entry in entries if entry.ref_number is not None})
    return ReferenceBundle(
        entries=entries,
        reference_count=len(entries),
        expected_reference_count=expected,
        missing_reference_ids=missing,
    )


def find_reference_section(pages: Iterable[str]) -> tuple[int | None, str]:
    page_texts = list(pages)
    last_match: tuple[int | None, str] | None = None
    for idx, page in enumerate(page_texts):
        text = page
        pos = 0
        while True:
            match = _HEADING_RE.search(text, pos)
            if not match:
                break
            pos = match.end()
            chunk = text[pos:pos + 500]
            if re.search(r"(?i)(\[\s*1\s*\]|\b1\.|\(1\)|[A-Z][a-z]+,\s+[A-Z]\.\s+[A-Za-z\-]+\s*\(\d{4}\))", chunk):
                last_match = (idx + 1, text[pos:])
    if last_match is None:
        return None, ""
    return last_match


def parse_reference_entries_from_pages(pages: list[str]) -> ReferenceBundle:
    ref_page, ref_text = find_reference_section(pages)
    if not ref_text:
        return ReferenceBundle(references_start_page=ref_page, entries=[], reference_count=0, expected_reference_count=0, missing_reference_ids=[])
    bundle = parse_reference_entries(ref_text)
    bundle.references_start_page = ref_page
    return bundle
