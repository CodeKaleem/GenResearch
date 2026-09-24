"""Best-effort table extraction with an optional pdfplumber enhancement."""
from __future__ import annotations

from typing import Any


def extract_tables(file_bytes: bytes) -> list[dict[str, Any]]:
    """Extract page/table rows when pdfplumber is installed.

    The ingestion pipeline remains usable without the optional dependency;
    callers receive an empty list and prose extraction continues.
    """
    try:
        import io
        import pdfplumber
    except ImportError:
        return []

    tables: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as document:
        for page_number, page in enumerate(document.pages, start=1):
            for table_number, rows in enumerate(page.extract_tables(), start=1):
                if rows:
                    tables.append({"page": page_number, "table": table_number, "rows": rows})
    return tables