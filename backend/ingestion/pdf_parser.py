"""Layout-aware PDF parsing built on the existing PyMuPDF dependency."""
from __future__ import annotations

from dataclasses import dataclass

import fitz

from .cleaner import clean_text


@dataclass(frozen=True)
class ParsedBlock:
    text: str
    page: int
    section_heading: str | None = None
    is_table: bool = False
    table_data: dict | None = None


import re

_SECTION_KEYWORDS = re.compile(
    r"(?i)^(?:[0-9IVXLCDM]+\.?\s*)?(?:abstract|introduction|background|related\s+work|"
    r"preliminaries|methodology|methods?|approach|model|architecture|system\s+design|"
    r"experimental\s+(?:setup|results)|experiments?|results|discussion|evaluation|"
    r"limitations|conclusion[s]?|future\s+work|acknowledgements?|references|appendix)\b"
)

_METADATA_INDICATORS = re.compile(
    r"(?i)(?:@|university|department|institute|academy|faculty|school|laboratory|"
    r"email|correspondence|author|ph\.d|dr\.|prof\.|ieee|acm|elsevier|springer|arxiv|vol\.\s*\d+)"
)


def _looks_like_heading(block: dict, page_number: int) -> bool:
    lines = block.get("lines", [])
    spans = [span for line in lines for span in line.get("spans", [])]
    if not spans:
        return False
    text = " ".join(span.get("text", "") for span in spans).strip()
    if not text or len(text) > 140:
        return False
    # Author lines, emails, and affiliations on page 1 are metadata, not section headings
    if _METADATA_INDICATORS.search(text):
        return False
    # If text explicitly matches academic section keywords
    if _SECTION_KEYWORDS.search(text):
        return True
    max_size = max(float(span.get("size", 0)) for span in spans)
    is_bold = any("bold" in span.get("font", "").lower() for span in spans)
    # Outside page 1, bold/large text is likely a heading
    if page_number > 1:
        return is_bold or max_size >= 13
    # On page 1, avoid treating isolated author names as section headings
    return max_size >= 15


def parse_pdf(file_bytes: bytes) -> list[ParsedBlock]:
    """Return cleaned text blocks with page and best-effort section metadata."""
    document = fitz.open(stream=file_bytes, filetype="pdf")
    blocks: list[ParsedBlock] = []
    current_heading: str | None = None
    try:
        for page_number, page in enumerate(document, start=1):
            for raw_block in page.get_text("dict").get("blocks", []):
                if raw_block.get("type") != 0:
                    continue
                text = clean_text("\n".join(
                    span.get("text", "")
                    for line in raw_block.get("lines", [])
                    for span in line.get("spans", [])
                ))
                if not text:
                    continue
                if _looks_like_heading(raw_block, page_number):
                    current_heading = text
                elif page_number == 1 and current_heading is None:
                    current_heading = "Title & Authors"
                blocks.append(ParsedBlock(text, page_number, current_heading))
    finally:
        document.close()
    return blocks