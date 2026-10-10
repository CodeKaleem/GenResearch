from __future__ import annotations

import re
import unicodedata
from typing import Iterable

import fitz

_ACCENT_MAP = {
    "`": "̀",
    "'": "́",
    "´": "́",
    "^": "̂",
    "~": "̃",
    '"': "̈",
    "ˇ": "̌",
    "˘": "̆",
    "¸": "̧",
    "¯": "̄",
    "˚": "̊",
}


def _recompose_spacing_accents(text: str) -> str:
    """Convert spacing accents like 'N´u' or 'Catal`a' into composed characters."""
    text = unicodedata.normalize("NFKC", text)
    for accent_char, combining in _ACCENT_MAP.items():
        text = re.sub(rf"([A-Za-z]){re.escape(accent_char)}([A-Za-z])", rf"\1{unicodedata.normalize('NFC', f'\2{combining}')}", text)
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")
    text = text.replace("\f", "\n")
    return text


def normalize_pdf_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = _recompose_spacing_accents(text)
    return text


def _readable_blocks(page: fitz.Page) -> list[dict]:
    # Try dict representation first
    raw_dict = page.get_text("dict")
    raw_blocks = raw_dict.get("blocks", []) if isinstance(raw_dict, dict) else []
    if raw_blocks:
        out: list[dict] = []
        for block in raw_blocks:
            if not isinstance(block, dict) or block.get("type", 0) != 0:
                continue
            lines = []
            for line in block.get("lines", []):
                span_text = "".join(span.get("text", "") for span in line.get("spans", []))
                if span_text.strip():
                    lines.append(span_text)
            text = "\n".join(lines).strip()
            if text:
                bbox = block.get("bbox", [0, 0, 0, 0])
                out.append({"x0": bbox[0], "y0": bbox[1], "text": text})
        if out:
            return out

    # Fallback to tuple representation from page.get_text("blocks")
    tuple_blocks = page.get_text("blocks")
    out = []
    for b in tuple_blocks:
        if isinstance(b, (tuple, list)) and len(b) >= 7:
            x0, y0, x1, y1, text, bno, btype = b[:7]
            if btype == 0 and text and text.strip():
                out.append({"x0": x0, "y0": y0, "text": text.strip()})
        elif isinstance(b, dict) and b.get("type", 0) == 0:
            text = b.get("text", "").strip()
            if text:
                bbox = b.get("bbox", [0, 0, 0, 0])
                out.append({"x0": bbox[0], "y0": bbox[1], "text": text})
    return out


def _cluster_blocks(blocks: Iterable[dict], page_w: float) -> list[str]:
    items = sorted(blocks, key=lambda b: (b["y0"], b["x0"]))
    clusters = []
    column_centers: list[tuple[float, list[str]]] = []
    for item in items:
        x = item["x0"]
        placed = False
        for idx, (center, lines) in enumerate(column_centers):
            if abs(x - center) < max(60, page_w * 0.12):
                lines.append(item["text"])
                column_centers[idx] = (center, lines)
                placed = True
                break
        if not placed:
            column_centers.append((x, [item["text"]]))
    for _, lines in sorted(column_centers, key=lambda c: c[0]):
        clusters.append("\n".join(lines))
    return clusters


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Return a normalized full-text representation of the PDF while preserving reading order."""
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return ""
    try:
        pages: list[str] = []
        for page_number, page in enumerate(document, start=1):
            page_w = page.rect.width
            blocks = _readable_blocks(page)
            if not blocks:
                pages.append("")
                continue
            # two-column pages: cluster blocks by horizontal position and join per cluster
            cluster_texts = _cluster_blocks(blocks, page_w)
            page_text = "\n\n".join(cluster_texts)
            page_text = normalize_pdf_text(page_text)
            page_text = re.sub(r"(?m)^\s*(?:Page\s*\d+|\d+)\s*$", "", page_text)
            page_text = re.sub(r"(?m)^\s*[-_=]{3,}\s*$", "", page_text)
            pages.append(page_text.strip())
        return "\n\n".join(p for p in pages if p).strip()
    finally:
        document.close()


def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Return a page-by-page list of normalized document text."""
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return []
    try:
        pages: list[str] = []
        for page in document:
            blocks = _readable_blocks(page)
            if not blocks:
                pages.append("")
                continue
            cluster_texts = _cluster_blocks(blocks, page.rect.width)
            page_text = "\n\n".join(cluster_texts)
            page_text = normalize_pdf_text(page_text)
            page_text = re.sub(r"(?m)^\s*(?:Page\s*\d+|\d+)\s*$", "", page_text)
            pages.append(page_text.strip())
        return pages
    finally:
        document.close()


def detect_no_text_layer(pdf_bytes: bytes) -> bool:
    text = extract_text_from_pdf(pdf_bytes)
    return not bool(text.strip())
