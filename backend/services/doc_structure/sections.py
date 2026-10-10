from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz

KNOWN_HEADINGS = {"abstract", "introduction", "conclusions", "acknowledgements", "appendix", "discussion", "limitations", "future work", "related work", "background"}


@dataclass
class Section:
    ordinal: int
    level: int
    title: str
    page_start: int | None = None
    page_end: int | None = None
    text: str = ""
    cited_refs: list[int] = field(default_factory=list)
    is_fallback_window: bool = False


def _looks_like_heading(text: str) -> bool:
    candidate = text.strip()
    if not candidate or len(candidate) > 180:
        return False
    lower = candidate.lower()
    if lower in KNOWN_HEADINGS:
        return True
    if re.match(r"^\d+(\.\d+)*\.?\s+[A-Z]", candidate):
        return True
    if re.match(r"^(abstract|introduction|conclusion|discussion|limitations|future work|acknowledgements|appendix)\b", lower, re.IGNORECASE):
        return True
    return False


def extract_sections(pdf_bytes: bytes, references_start_page: int | None = None) -> list[Section]:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return []
    try:
        body_pages = list(document)
        sections: list[Section] = []
        headings: list[tuple[int, str, int, int]] = []
        for page_idx, page in enumerate(body_pages, start=1):
            raw_dict = page.get_text("dict")
            blocks = raw_dict.get("blocks", []) if isinstance(raw_dict, dict) else []
            if blocks:
                for block in blocks:
                    if not isinstance(block, dict) or block.get("type", 0) != 0:
                        continue
                    text = " ".join(span.get("text", "").strip() for line in block.get("lines", []) for span in line.get("spans", [])).strip()
                    if _looks_like_heading(text):
                        headings.append((page_idx, text, page_idx, page_idx))
            else:
                for b in page.get_text("blocks"):
                    if isinstance(b, (tuple, list)) and len(b) >= 7 and b[6] == 0:
                        text = str(b[4]).strip()
                        if _looks_like_heading(text):
                            headings.append((page_idx, text, page_idx, page_idx))
        if len(headings) >= 3:
            ordered = sorted(headings, key=lambda x: x[0])
            for idx, (page_num, title, _, _) in enumerate(ordered, start=1):
                section_text = ""
                sections.append(Section(ordinal=idx, level=1, title=title, page_start=page_num, page_end=page_num, text=section_text))
        if not sections:
            return _fallback_windows(body_pages, references_start_page)
        ref_start = references_start_page
        if ref_start is not None:
            active_pages = body_pages[: max(0, ref_start - 1)]
        else:
            active_pages = body_pages
        section_map = []
        start_page = 1
        for idx, section in enumerate(sections, start=1):
            section.page_start = start_page if section.page_start is None else section.page_start
            section.page_end = section.page_start
            text_parts = []
            for page_idx in range(section.page_start, min(section.page_end if section.page_end else section.page_start, len(active_pages)) + 1):
                text = active_pages[page_idx - 1].get_text("text") if page_idx - 1 < len(active_pages) else ""
                if text:
                    text_parts.append(text)
            section.text = "\n\n".join(text_parts)
            section_map.append(section)
        return section_map
    finally:
        document.close()


def _fallback_windows(body_pages: list[fitz.Page], references_start_page: int | None) -> list[Section]:
    size = max(2, min(4, len(body_pages) or 2))
    sections: list[Section] = []
    end_limit = references_start_page - 1 if references_start_page else len(body_pages)
    pages = body_pages[:end_limit]
    for idx in range(0, len(pages), size):
        window = pages[idx: idx + size]
        title = f"Page window {idx + 1}-{idx + len(window)}"
        text = "\n\n".join(page.get_text("text") for page in window if page.get_text("text").strip())
        sections.append(Section(ordinal=len(sections) + 1, level=1, title=title, page_start=(idx + 1), page_end=(idx + len(window)), text=text, is_fallback_window=True))
    return sections
