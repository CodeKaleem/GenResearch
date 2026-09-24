"""Pre-index relevance checks for uploaded documents."""
from __future__ import annotations

import re


def check_relevance_preview(title: str, preview: str, declared_topic: str) -> dict:
    """Cheap deterministic gate used before an optional model-assisted check."""
    topic_terms = {
        term.lower()
        for term in re.findall(r"[a-zA-Z]{4,}", declared_topic)
    }
    haystack = f"{title} {preview}".lower()
    matches = sorted(term for term in topic_terms if term in haystack)
    relevant = bool(matches) or not topic_terms
    return {
        "relevant": relevant,
        "reason": "Matched topic terms: " + ", ".join(matches) if matches else "No declared topic terms matched the preview.",
    }