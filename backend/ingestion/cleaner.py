"""Deterministic cleanup for text extracted from academic PDFs."""
from __future__ import annotations

import re


LIGATURE_FIXES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}


def clean_text(text: str) -> str:
    """Normalize common PDF artifacts without rewriting document content."""
    for source, replacement in LIGATURE_FIXES.items():
        text = text.replace(source, replacement)
    text = re.sub(r"-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()