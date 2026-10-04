# ============================================================
# GenResearch — PDF Text Extractor
# Uses PyMuPDF (fitz) for fast, accurate extraction
# ============================================================
import asyncio

import fitz  # PyMuPDF


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract PDF text without blocking the event loop."""
    return await asyncio.to_thread(_extract_text_from_pdf, file_bytes)


async def get_pdf_page_count(file_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    def count_pages() -> int:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count

    return await asyncio.to_thread(count_pages)
