from __future__ import annotations

import re

INTENT_PATTERNS = {
    "citations": [
        "extract the citations",
        "list all references",
        "which papers are cited",
        "cite", "bibliography", "references",
    ],
    "gaps": [
        "research gap",
        "open problems",
        "what's missing",
        "what is missing in the field",
        "gap in the literature",
        "limitations",
    ],
    "improvements": [
        "how can this paper be improved",
        "weaknesses",
        "critique",
        "improvement points",
        "give me",
        "points to improve",
    ],
    "future_work": ["future work", "what should be done next"],
    "contributions": ["contributions", "main contributions"],
    "summary": ["summary", "give me a summary"],
    "sections_list": ["list sections", "section list", "table of contents"],
    "items_list": ["list tables", "list figures", "figures", "tables"],
}


def parse_requested_count(query: str) -> int | None:
    if not query:
        return None
    match = re.search(r"(?i)(?:top\s+|at\s+least\s+)?(\d+)\s*(?:points?|references?|items?|sections?|papers?)?", query)
    if not match:
        return None
    value = int(match.group(1))
    return value if value > 0 else None


def classify_intent(query: str) -> str:
    text = (query or "").lower().strip()
    if not text:
        return "qa"
    for intent, patterns in INTENT_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            return intent
    return "qa"


def route_query(query: str) -> tuple[str, int | None]:
    return classify_intent(query), parse_requested_count(query)
