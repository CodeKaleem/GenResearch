"""Chat intent routing.

The previous version matched bare substrings ("cite", "references", "figures",
"tables", "give me" ...), so ordinary questions such as "What do the figures
show?" or "Give me the main findings" were hijacked by structure handlers.

Rules now:
* Structured intents (citations / sections_list / items_list) only fire when the
  user clearly asks to *list or extract* them.
* Broad intents (summary, gaps, improvements, future_work, contributions) still
  go through RAG, but with wider, page-diversified retrieval (see rag_service).
* Everything else is plain "qa".
"""
from __future__ import annotations

import re

STRUCTURED_INTENTS = {"citations", "sections_list", "items_list"}
BROAD_INTENTS = {"summary", "gaps", "improvements", "future_work", "contributions"}

_LIST_VERB = r"(?:list|extract|show|give|get|print|enumerate)"

# Order matters: first match wins.
_PATTERNS: list[tuple[str, list[str]]] = [
    ("citations", [
        rf"\b{_LIST_VERB}\b.{{0,40}}\b(?:references|citations|bibliography)\b",
        r"\bwhich (?:papers|works|studies|articles) (?:are|were) cited\b",
        r"\bbibliography\b",
        r"^\s*(?:references|citations)\s*\??\s*$",
    ]),
    ("sections_list", [
        rf"\b{_LIST_VERB}\b.{{0,25}}\b(?:sections|chapters|headings)\b",
        r"\btable of contents\b",
        r"\bsection list\b",
        r"\bwhat sections\b",
    ]),
    ("items_list", [
        rf"\b{_LIST_VERB}\b.{{0,25}}\b(?:tables|figures)\b",
        r"\bhow many (?:tables|figures)\b",
        r"\b(?:table|figure) list\b",
    ]),
    ("gaps", [
        r"\bresearch gaps?\b",
        r"\bopen problems?\b",
        r"\bgaps? in the (?:literature|field|research)\b",
        r"\bwhat(?:'s| is) missing\b",
        r"\blimitations?\b",
    ]),
    ("improvements", [
        r"\bhow (?:can|could|should) (?:this|the) (?:paper|study|work|research) be improved\b",
        r"\bweakness(?:es)?\b",
        r"\bcritique\b",
        r"\bpoints? to improve\b",
        r"\bimprovement points?\b",
    ]),
    ("future_work", [
        r"\bfuture work\b",
        r"\bwhat should be done next\b",
        r"\bnext steps\b",
    ]),
    ("contributions", [
        r"\bcontributions?\b",
    ]),
    ("summary", [
        r"\bsummary\b",
        r"\bsummari[sz]e\b",
        r"\boverview of (?:the|this)\b",
        r"\btl;?dr\b",
    ]),
]

_COMPILED = [(intent, [re.compile(p, re.IGNORECASE) for p in patterns]) for intent, patterns in _PATTERNS]

_COUNT_RE = re.compile(
    r"(?i)\b(?:top|first|at\s+least|exactly)?\s*(\d{1,3})\s+"
    r"(?:research\s+)?(?:points?|references?|items?|sections?|papers?|gaps?|"
    r"contributions?|improvements?|weaknesses|limitations?|findings?)\b"
)


def parse_requested_count(query: str) -> int | None:
    """Return N for requests like "top 5 research gaps"; ignore stray numbers like "Table 2" or "2020"."""
    if not query:
        return None
    match = _COUNT_RE.search(query)
    if not match:
        return None
    value = int(match.group(1))
    return value if 0 < value <= 100 else None


def classify_intent(query: str) -> str:
    text = (query or "").strip()
    if not text:
        return "qa"
    for intent, patterns in _COMPILED:
        if any(pattern.search(text) for pattern in patterns):
            return intent
    return "qa"


def route_query(query: str) -> tuple[str, int | None]:
    return classify_intent(query), parse_requested_count(query)
