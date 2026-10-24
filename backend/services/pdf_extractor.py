# ============================================================
# GenResearch — PDF Text Extractor
# Uses PyMuPDF (fitz) for fast, accurate extraction
# ============================================================
import asyncio

import fitz  # PyMuPDF


def extract_text_and_diagnose(file_bytes: bytes) -> tuple[str, str | None]:
    """Extract text from PDF and return (text, diagnostic_reason_if_empty).

    Diagnoses why text could not be extracted instead of reporting UNKNOWN:
    - empty_file: 0 or fewer bytes
    - corrupt_pdf: cannot be opened by PDF parser
    - encrypted_pdf: document is password-protected
    - zero_pages: document contains 0 pages
    - scanned_pdf_no_text_layer: document has pages/images, but no text layer (requires OCR)
    """
    if not file_bytes or len(file_bytes) < 10:
        return "", "empty_or_truncated_file (under 10 bytes)"

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return "", f"corrupted_pdf_file ({type(e).__name__}: {e})"

    if doc.is_encrypted:
        doc.close()
        return "", "password_protected_encrypted_pdf"

    if len(doc) == 0:
        doc.close()
        return "", "zero_page_pdf"

    pages: list[str] = []
    has_images = False
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
        if not has_images and len(page.get_images()) > 0:
            has_images = True
    doc.close()

    extracted = "\n\n".join(pages).strip()
    if extracted:
        return extracted, None

    if has_images:
        diagnostic = "scanned_pdf_no_text_layer (document contains scanned images without OCR text layer)"
    else:
        diagnostic = "empty_text_layer (document has no text content or font encodings were unreadable)"

    return "", diagnostic


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    extracted, _ = extract_text_and_diagnose(file_bytes)
    return extracted


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
