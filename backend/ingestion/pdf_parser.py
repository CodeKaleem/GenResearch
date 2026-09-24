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


def _looks_like_heading(block: dict) -> bool:
    lines = block.get("lines", [])
    spans = [span for line in lines for span in line.get("spans", [])]
    if not spans:
        return False
    text = " ".join(span.get("text", "") for span in spans).strip()
    if not text or len(text) > 160:
        return False
    max_size = max(float(span.get("size", 0)) for span in spans)
    is_bold = any("bold" in span.get("font", "").lower() for span in spans)
    return is_bold or max_size >= 13


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
                if _looks_like_heading(raw_block):
                    current_heading = text
                blocks.append(ParsedBlock(text, page_number, current_heading))
    finally:
        document.close()
    return blocks