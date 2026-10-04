"""Small shared text utilities for sentence-level draft processing."""
from __future__ import annotations

import re


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_ABBREVIATION = re.compile(
    r"\b(et al|e\.g|i\.e|etc|vs|cf|Dr|Mr|Mrs|Ms|Prof|Fig|No|U\.S|U\.K)\.",
    re.IGNORECASE,
)
_DECIMAL_POINT = re.compile(r"(?<=\d)\.(?=\d)")
_INITIAL_SEQUENCE = re.compile(r"(?<![A-Za-z])(?:[A-Z]\.\s*){2,}(?=[A-Z][a-z])")
_SENTINEL = "\u0000"


def split_sentences(text: str) -> list[str]:
    """Split prose without treating academic abbreviations, decimals, or initials as sentence ends."""
    protected = _ABBREVIATION.sub(
        lambda match: match.group(0).replace(".", _SENTINEL), text
    )
    protected = _DECIMAL_POINT.sub(_SENTINEL, protected)
    protected = _INITIAL_SEQUENCE.sub(
        lambda match: match.group(0).replace(".", _SENTINEL), protected
    )
    return [part.replace(_SENTINEL, ".") for part in _SENTENCE_BOUNDARY.split(protected)]