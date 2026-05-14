# ============================================================
# GenResearch — PDF Text Extractor
# Uses PyMuPDF (fitz) for fast, accurate extraction
# ============================================================
import fitz  # PyMuPDF


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF provided as raw bytes.
    Returns concatenated text from every page.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)


async def get_pdf_page_count(file_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count
