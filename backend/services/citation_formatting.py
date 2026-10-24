# ============================================================
# GenResearch — Citation Formatting
# Resolves internal [CR-001] registry tags into proper in-text
# citations, flags uncited / unsupported prose safely, and builds
# a properly formatted, alphabetized reference list.
# ============================================================
from __future__ import annotations

import re
from dataclasses import dataclass

from services.text_utils import split_sentences

# ------------------------------------------------------------
# Tag patterns
# ------------------------------------------------------------
_ID = r"CR-(?:[A-F0-9]{12}|\d{3})"  # longest form first so findall() never truncates
CITATION_TAG = re.compile(rf"\[({_ID})\]", re.IGNORECASE)

# "[CR-A, CR-B]" / "[CR-A; CR-B]"  ->  "[CR-A][CR-B]"
_GROUPED_TAGS = re.compile(rf"\[\s*{_ID}(?:\s*[,;]\s*{_ID})+\s*\]", re.IGNORECASE)

# "claim. [CR-A]"  ->  "claim [CR-A]."
_TAGS_AFTER_PUNCT = re.compile(
    rf"([.!?])\s+((?:\[{_ID}\])(?:\s*\[{_ID}\])*)(?=\s|$)", re.IGNORECASE
)

_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[,.]\d+)*(?:\s?%|\s+percent)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ENTITY = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z][a-z]+[A-Z][A-Za-z0-9]*|"
    r"[A-Z]{2,}[A-Z0-9-]*|[A-Z][A-Z0-9-]*\d[A-Z0-9-]*)\b"
)
_DUPLICATE_CITATION_NEEDED = re.compile(
    r"\[CITATION NEEDED\](?:\s*\[CITATION NEEDED\])+"
)

# Free-form "(Surname et al., 2020)" style citations written by the model.
_FREEFORM_CITATION = re.compile(
    r"\(\s*(?P<first>[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+)"
    r"(?:\s+et\s+al\.?|\s*(?:,|&|and)\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+)?"
    r",\s*(?P<year>\d{4})[a-z]?\s*\)"
)


# ------------------------------------------------------------
# Tag normalisation
# ------------------------------------------------------------
def normalize_citation_tags(text: str) -> str:
    """Make model-written tags uniform so later steps can rely on them.

    - splits grouped tags: [CR-A, CR-B] -> [CR-A][CR-B]
    - upper-cases tag ids
    - moves tags that trail sentence punctuation back before it
    """

    def split_group(match: re.Match) -> str:
        ids = re.findall(_ID, match.group(0), flags=re.IGNORECASE)
        return "".join(f"[{item.upper()}]" for item in ids)

    text = _GROUPED_TAGS.sub(split_group, text)
    text = CITATION_TAG.sub(lambda m: f"[{m.group(1).upper()}]", text)
    text = _TAGS_AFTER_PUNCT.sub(r" \2\1", text)
    return text


def normalize_registry_citation_ids(text: str, citation_registry: list[dict]) -> str:
    """Wrap bare citation IDs only when they identify a source in the registry."""
    text = normalize_citation_tags(text)
    valid_ids = {
        str(entry.get("id", "")).upper()
        for entry in citation_registry
        if entry.get("id")
    }
    for citation_id in sorted(valid_ids, key=len, reverse=True):
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_\[])({re.escape(citation_id)})(?![A-Za-z0-9_\]])",
            re.IGNORECASE,
        )
        text = pattern.sub(lambda match: f"[{match.group(1).upper()}]", text)
    return text


def drop_unknown_citation_tags(text: str, valid_source_ids: set[str]) -> str:
    """Remove well-formed [CR-...] tags that are not in the registry."""
    valid = {item.upper() for item in valid_source_ids}
    text = CITATION_TAG.sub(
        lambda m: m.group(0) if m.group(1).upper() in valid else "", text
    )
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    return text


# ------------------------------------------------------------
# Marker helpers
# ------------------------------------------------------------
def _registry_author_year_keys(citation_registry: list[dict] | None) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for entry in citation_registry or []:
        authors = _split_authors(entry.get("authors", ""))
        year = str(entry.get("year") or "")
        if authors and year:
            keys.add((_surname(authors[0]).casefold(), year[:4]))
    return keys


def flag_unverified_freeform_citations(
    text: str, citation_registry: list[dict] | None = None
) -> str:
    """Replace author/year citations that cannot be checked against the registry.

    A free-form citation such as "(Montgomery & Biklé, 2021)" is kept when its
    first surname and year match a registry entry; otherwise it is flagged.
    """
    known = _registry_author_year_keys(citation_registry)

    def replace(match: re.Match) -> str:
        if (match.group("first").casefold(), match.group("year")) in known:
            return match.group(0)
        return "[CITATION NEEDED]"

    return _FREEFORM_CITATION.sub(replace, text)


def collapse_duplicate_citation_markers(text: str) -> str:
    """Collapse adjacent repeated citation-needed markers into one."""
    return _DUPLICATE_CITATION_NEEDED.sub("[CITATION NEEDED]", text)


def _split_sentences(text: str) -> list[str]:
    """Compatibility wrapper for callers of the original formatter helper."""
    return split_sentences(text)


# Catches placeholder-template syntax the draft agent copies literally
# instead of filling in — e.g. "[Author A, Year] [CR-00X]".
_PLACEHOLDER_AUTHOR_BRACKET = re.compile(r"\[\s*Author\s+[A-Za-z]\s*,?\s*Year\s*\]", re.IGNORECASE)
_PLACEHOLDER_AUTHOR_YEAR = re.compile(
    r"[\[(]\s*Authors?\s*,?\s*Year\s*[\])]", re.IGNORECASE
)
_PLACEHOLDER_CITATION = re.compile(
    r"\[\s*(?:citation|cite|reference|source)(?:\s+(?:needed|here|to\s+add|insert))?\s*\]",
    re.IGNORECASE,
)
_NEAR_MISS_CR_TAG = re.compile(
    r"\[CR-(?!\d{3}\]|[A-F0-9]{12}\])[^\]]*\]", re.IGNORECASE
)


def flag_placeholder_template_syntax(text: str) -> str:
    """Replace copied-literally exemplar placeholder syntax with an honest flag."""
    text = _PLACEHOLDER_AUTHOR_BRACKET.sub("[CITATION NEEDED]", text)
    text = _PLACEHOLDER_AUTHOR_YEAR.sub("[CITATION NEEDED]", text)
    text = _PLACEHOLDER_CITATION.sub("[CITATION NEEDED]", text)
    text = _NEAR_MISS_CR_TAG.sub("[CITATION NEEDED]", text)
    return text


def _normalize_grounding_text(text: str) -> str:
    return " ".join(re.findall(r"\d+(?:[,.]\d+)*%|[a-z0-9]+", text.lower()))


_CITING_AUTHOR_PHRASE = re.compile(
    r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+)?\s+et al\.?",
)
_SINGLE_CAPITALIZED_ENTITY = re.compile(r"\b[A-Z][a-z][A-Za-z0-9-]{3,}\b")
_TERMINAL_PUNCTUATION = re.compile(r"([.!?]+[\"'’”\)\]]*)$")
_TRAILING_MARKER = re.compile(r"([.!?])\s+(\[CITATION NEEDED\])(?=\s|$)")


def _mark_before_terminal_punctuation(sentence: str) -> str:
    sentence = re.sub(r"\s*\[CITATION NEEDED\]", "", sentence).rstrip()
    match = _TERMINAL_PUNCTUATION.search(sentence)
    if not match:
        return f"{sentence.rstrip()} [CITATION NEEDED]"
    body = sentence[: match.start()].rstrip()
    return f"{body} [CITATION NEEDED]{match.group(1)}"


# ------------------------------------------------------------
# Markdown-aware sentence splitting + uncited-sentence flagging
# ------------------------------------------------------------
_DOT = "\uE000"  # private-use placeholder for "protected" periods

_DOT_PROTECTORS = [
    re.compile(r"\b10\.\d{4,9}/\S+"),  # DOIs
    re.compile(
        r"\b(?:e\.g|i\.e|et al|vs|cf|Fig|Figs|Eq|Eqs|Dr|Prof|approx|ca|resp)\."
    ),  # common abbreviations
    re.compile(r"\b[A-Z]\.(?=\s?[A-Z])"),  # initials: "D. R. Montgomery"
    re.compile(r"(?<=\d)\.(?=\d)"),  # decimals: 3.5
]

_SENTENCE_SPLIT = re.compile(
    r"(?:(?<=[.!?])|(?<=[.!?][\"'’”\)\]]))\s+(?=[\"“'(\[]?[A-Z0-9])"
)


def _protect_dots(text: str) -> str:
    for pattern in _DOT_PROTECTORS:
        text = pattern.sub(lambda m: m.group(0).replace(".", _DOT), text)
    return text


def split_prose_sentences(text: str) -> list[str]:
    """Split prose into sentences without breaking initials, et al., DOIs or decimals."""
    parts = _SENTENCE_SPLIT.split(_protect_dots(text))
    return [part.replace(_DOT, ".").strip() for part in parts if part.strip()]


_HEADING_LINE = re.compile(r"^\s*#{1,6}\s")
_REFERENCE_HEADING = re.compile(
    r"^\s*#{1,6}\s*\**\s*(?:references|bibliography|works cited)\b", re.IGNORECASE
)
_RULE_LINE = re.compile(r"^\s*(?:[-*_]\s*){3,}$")
_LABEL_LINE = re.compile(r"^\s*\*\*[^*]{1,80}\*\*:?\s*$")
_TABLE_ROW = re.compile(r"^\s*\|")
_LIST_PREFIX = re.compile(r"^(\s*(?:[-*+•]|\d+[.)])\s+)")
_MIN_CLAIM_WORDS = 6



# Matches resolved author-year in-text citations produced by resolve_in_text_citations,
# e.g. "(Smith et al., 2021)" or "(Smith & Jones, 2021)" or "(Smith, 2021)".
_RESOLVED_CITATION = re.compile(
    r"\([A-Z][A-Za-z\u00C0-\u024F'\-]+(?:\s+et\s+al\.?|(?:\s*(?:,|&|and)\s*[A-Z][A-Za-z\u00C0-\u024F'\-]+)*)?"
    r",\s*\d{4}[a-z]?\)",
    re.IGNORECASE,
)

_META_OR_SCOPE_PATTERNS = [
    # Paper's own aims and objectives
    re.compile(r"\b(?:this\s+(?:paper|study|proposal|work|review|article|chapter|section|thesis|report)\s+(?:aims|proposes|investigates|explores|evaluates|presents|examines|reviews|discusses|outlines|describes|focuses|seeks|attempts|addresses))\b", re.IGNORECASE),
    re.compile(r"\b(?:the\s+(?:aim|goal|purpose|objective|focus|scope|contribution|structure)\s+of\s+this\s+(?:paper|study|proposal|work|review|article|research|report))\b", re.IGNORECASE),
    re.compile(r"\b(?:our\s+(?:goal|aim|purpose|objective|approach|work|study|pipeline|methodology|framework|system|contribution))\s+(?:is|focuses|consists|aims)\b", re.IGNORECASE),
    re.compile(r"\b(?:we\s+(?:propose|aim|investigate|examine|explore|present|introduce|develop|evaluate|describe|outline|hypothesize|argue|discuss|detail))\b", re.IGNORECASE),
    re.compile(r"\b(?:in\s+this\s+(?:paper|study|work|proposal|review|article|section),\s*we)\b", re.IGNORECASE),
    # Structure and organization
    re.compile(r"\b(?:the\s+(?:remainder|rest)\s+of\s+this\s+(?:paper|section|document|article)\s+is\s+(?:organized|structured))\b", re.IGNORECASE),
    re.compile(r"\b(?:section\s+\d+|in\s+section\s+\d+|in\s+this\s+section)\b", re.IGNORECASE),
    re.compile(r"\b(?:organized\s+as\s+follows|structured\s+as\s+follows)\b", re.IGNORECASE),
    re.compile(r"\b(?:the\s+following\s+sections?\s+(?:describe|present|discuss|detail|outline))\b", re.IGNORECASE),
    # Methods of this paper
    re.compile(r"\b(?:we\s+(?:conducted|performed|utilized|employed|applied|implemented|collected|analyzed|gathered|trained|evaluated|tested))\b", re.IGNORECASE),
    re.compile(r"\b(?:in\s+our\s+(?:methodology|experiments|approach|evaluation|implementation|study|framework))\b", re.IGNORECASE),
    re.compile(r"\b(?:data\s+(?:was|were)\s+(?:collected|gathered|analyzed|extracted)\s+using)\b", re.IGNORECASE),
    # Scope and boundaries
    re.compile(r"\b(?:the\s+scope\s+of\s+this\s+(?:paper|study|review|work)\s+is)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+(?:review|study|paper)\s+is\s+limited\s+to)\b", re.IGNORECASE),
    re.compile(r"\b(?:we\s+(?:restrict|limit|confine)\s+our\s+(?:focus|attention|scope|discussion))\b", re.IGNORECASE),
]


def is_meta_or_scope_sentence(sentence: str) -> bool:
    """Return True if sentence is about the paper's own aims, structure, methods or scope."""
    cleaned = sentence.strip()
    return any(p.search(cleaned) is not None for p in _META_OR_SCOPE_PATTERNS)


class UncitedSentencesResult(tuple):
    """Result of flag_uncited_sentences.

    Behaves as a 3-tuple (text, flagged_count, sentence_count) for complete
    backward-compatibility, while exposing .review_list containing uncited claims.
    """
    def __new__(cls, text: str, flagged_count: int, sentence_count: int, review_list: list[str] | None = None):
        return super().__new__(cls, (text, flagged_count, sentence_count))

    def __init__(self, text: str, flagged_count: int, sentence_count: int, review_list: list[str] | None = None):
        self.text = text
        self.flagged_count = flagged_count
        self.sentence_count = sentence_count
        self.review_list = list(review_list or [])


def flag_uncited_sentences(
    text: str, valid_source_ids: set[str], add_markers: bool = False
) -> UncitedSentencesResult:
    """Collect uncited factual claims without cluttering the paper with [CITATION NEEDED].

    Skips sentences describing the paper's own aims, structure, methods and scope.
    Collects uncited claims into .review_list for author review.
    If add_markers is True, appends [CITATION NEEDED] to flagged sentences (legacy test mode).
    Returns UncitedSentencesResult (unpacks as (text, flagged_count, sentence_count)).
    """
    valid = {item.upper() for item in valid_source_ids}
    flagged = total = 0
    in_references = False
    output: list[str] = []
    review_list: list[str] = []

    for line in text.split("\n"):
        if not line.strip() or _RULE_LINE.match(line) or _LABEL_LINE.match(line) or _TABLE_ROW.match(line):
            output.append(line)
            continue
        if _HEADING_LINE.match(line):
            in_references = bool(_REFERENCE_HEADING.match(line))
            output.append(line)
            continue
        if in_references:
            output.append(line)
            continue

        prefix = ""
        body = line
        list_match = _LIST_PREFIX.match(line)
        if list_match:
            prefix = list_match.group(1)
            body = line[list_match.end():]

        checked: list[str] = []
        for sentence in split_prose_sentences(body):
            words = CITATION_TAG.sub("", sentence).split()
            if len(words) < _MIN_CLAIM_WORDS:
                checked.append(sentence)
                continue

            # Skip sentences describing the paper's own aims, structure, methods, scope
            if is_meta_or_scope_sentence(sentence):
                checked.append(sentence)
                continue

            total += 1
            # Accept either a raw [CR-...] tag or a resolved (Author, Year) citation
            ids = {item.upper() for item in CITATION_TAG.findall(sentence)}
            has_raw_tag = bool(ids & valid)
            has_resolved = bool(_RESOLVED_CITATION.search(sentence))
            if has_raw_tag or has_resolved:
                checked.append(sentence)
                continue

            flagged += 1
            review_list.append(sentence.strip())
            if add_markers:
                checked.append(_mark_before_terminal_punctuation(sentence))
            else:
                checked.append(sentence)
        output.append(prefix + " ".join(checked))

    return UncitedSentencesResult("\n".join(output), flagged, total, review_list)


def clean_citation_needed_markers(text: str) -> tuple[str, list[str]]:
    """Strip [CITATION NEEDED] markers from final text and extract claims into a review list.

    Guarantees [CITATION NEEDED] is never left in the final paper text.
    """
    review_list: list[str] = []
    for line in text.split("\n"):
        if "[CITATION NEEDED]" in line or "(citation needed)" in line.lower():
            for s in split_prose_sentences(line):
                if "[CITATION NEEDED]" in s or "(citation needed)" in s.lower():
                    cleaned_claim = re.sub(r"\s*\[CITATION NEEDED\]", "", s, flags=re.IGNORECASE)
                    cleaned_claim = re.sub(r"\s*\(citation needed\)", "", cleaned_claim, flags=re.IGNORECASE).strip()
                    if cleaned_claim:
                        review_list.append(cleaned_claim)

    cleaned_text = re.sub(r"\s*\[CITATION NEEDED\]", "", text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"\s*\(citation needed\)", "", cleaned_text, flags=re.IGNORECASE)
    return cleaned_text, review_list



def find_unsupported_numbers(
    text: str,
    evidence_by_source: dict[str, str],
    valid_source_ids: set[str],
    extra_allowed: str = "",
) -> list[str]:
    """Report numbers in cited sentences that never appear in the cited evidence.

    Advisory only: the text is not modified.
    """
    valid = {item.upper() for item in valid_source_ids}
    issues: list[str] = []
    sentences = [
        sentence
        for line in text.split("\n")
        if line.strip() and not _HEADING_LINE.match(line)
        for sentence in split_prose_sentences(line)
    ]
    for sentence in sentences:
        ids = {item.upper() for item in CITATION_TAG.findall(sentence)} & valid
        if not ids:
            continue
        evidence = " ".join(evidence_by_source.get(item, "") for item in ids)
        if not evidence.strip():
            continue
        allowed = f" {_normalize_grounding_text(evidence + ' ' + extra_allowed)} "
        body = CITATION_TAG.sub("", sentence)
        for raw in dict.fromkeys(_NUMBER.findall(body)):
            is_percent = "%" in raw or "percent" in raw.lower()
            core = re.sub(r"\s?%|\s+percent", "", raw, flags=re.IGNORECASE)
            if len(re.sub(r"\D", "", core)) < 2 and not is_percent:
                continue  # skip tiny counts like "3"
            token = _normalize_grounding_text(core)
            if not token:
                continue
            if f" {token} " in allowed or f" {token}% " in allowed:
                continue
            issues.append(f'"{raw.strip()}" not found in cited excerpts: {sentence[:140]}')
    return list(dict.fromkeys(issues))


# ------------------------------------------------------------
# Grounding of specifics (kept for callers of the original module)
# ------------------------------------------------------------
@dataclass(frozen=True)
class GroundingResult:
    text: str
    removed_claims: list[str]
    flagged_count: int
    sentence_count: int
    preserved_empty_section: bool = False


def _entity_candidates(body: str) -> list[str]:
    body = body.replace("[CITATION NEEDED]", "")
    body = _CITING_AUTHOR_PHRASE.sub("", body)
    first_word = re.search(r"\S+", body)
    sentence_start = first_word.start() if first_word else -1
    candidates = [
        match.group(0)
        for match in _ENTITY.finditer(body)
        if match.start() != sentence_start
    ]
    candidates.extend(
        match.group(0)
        for match in _SINGLE_CAPITALIZED_ENTITY.finditer(body)
        if match.start() != sentence_start
    )
    return candidates


def ground_ungrounded_specifics(
    text: str,
    evidence_by_source: dict[str, str],
    valid_source_ids: set[str],
    topic: str = "",
) -> GroundingResult:
    """Flag generic uncited prose and remove unsupported specifics lacking a valid source."""
    text = _TRAILING_MARKER.sub(r" \2\1", text)
    sentences = [sentence.strip() for sentence in split_sentences(text) if sentence.strip()]
    checked_sentences: list[str] = []
    removed_claims: list[str] = []
    flagged_count = 0

    for sentence in sentences:
        citation_ids = {item.upper() for item in CITATION_TAG.findall(sentence)}
        valid_ids = citation_ids & valid_source_ids
        body = CITATION_TAG.sub("", sentence)
        evidence = " ".join(evidence_by_source.get(cid, "") for cid in valid_ids)
        evidence_available = bool(evidence.strip())
        allowed = _normalize_grounding_text(f"{evidence} {topic}")
        specifics = _NUMBER.findall(body) + _entity_candidates(body)
        # Only run specifics grounding when evidence text was actually retrieved.
        unsupported_specifics = (
            [
                specific
                for specific in dict.fromkeys(specifics)
                if _normalize_grounding_text(specific) not in allowed
            ]
            if evidence_available
            else []
        )
        needs_flag = (
            not valid_ids
            or bool(citation_ids - valid_source_ids)
            or bool(unsupported_specifics)
        )

        if unsupported_specifics and not valid_ids:
            removed_claims.append(sentence)
            flagged_count += 1
            continue
        if needs_flag:
            sentence = _mark_before_terminal_punctuation(sentence)
            flagged_count += 1
        checked_sentences.append(sentence)

    preserved_empty = bool(sentences and not checked_sentences and removed_claims)
    if preserved_empty:
        checked_sentences = sentences
        removed_claims = []

    return GroundingResult(
        text=collapse_duplicate_citation_markers(" ".join(checked_sentences)),
        removed_claims=removed_claims,
        flagged_count=flagged_count,
        sentence_count=len(sentences),
        preserved_empty_section=preserved_empty,
    )


def flag_ungrounded_specifics(
    text: str,
    evidence_by_source: dict[str, str],
    valid_source_ids: set[str],
    topic: str = "",
) -> str:
    """Flag sentences without valid citations or with unsupported specifics."""
    return ground_ungrounded_specifics(
        text, evidence_by_source, valid_source_ids, topic
    ).text


# ------------------------------------------------------------
# Author handling
# ------------------------------------------------------------
# Matches common academic author-list formats: "Surname, F. M." units,
# e.g. "Tay, Y., Dehghani, M., Bahri, D.".
_AUTHOR_UNIT = re.compile(r"([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]+),\s*((?:[A-Z]\.\s*)+)")


def _split_authors(authors: str) -> list[str]:
    """Best-effort split of a free-text author string into individual names."""
    if not authors or authors.strip().lower() == "unknown":
        return []

    normalized = re.sub(r"\s*(?:&|;)\s*|\s+and\s+", ", ", authors)

    units = _AUTHOR_UNIT.findall(normalized)
    if units:
        return [f"{surname}, {initials.strip()}" for surname, initials in units]

    # If no "Surname, F." pattern is detected, assume a comma-separated list.
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _surname(name: str) -> str:
    """Pull a surname out of 'Last, F.' or 'First Last' formats."""
    name = name.strip()
    if "," in name:
        return name.split(",", 1)[0].strip()
    tokens = name.split()
    return tokens[-1] if tokens else name


# ------------------------------------------------------------
# In-text citations
# ------------------------------------------------------------
def format_in_text_citation(entry: dict) -> str:
    """Render one registry entry as an APA-style parenthetical citation."""
    year = entry.get("year") or "n.d."
    authors = _split_authors(entry.get("authors", ""))

    if not authors:
        title = (entry.get("title") or "Untitled").strip()
        short_title = title if len(title) <= 40 else title[:37].rstrip() + "..."
        return f'("{short_title}", {year})'

    if len(authors) == 1:
        return f"({_surname(authors[0])}, {year})"
    if len(authors) == 2:
        return f"({_surname(authors[0])} & {_surname(authors[1])}, {year})"
    return f"({_surname(authors[0])} et al., {year})"


_ADJACENT_CITES = re.compile(
    r"\(([^()]*?(?:\d{4}[a-z]?|n\.d\.))\)(?:\s*,?\s*)\(([^()]*?(?:\d{4}[a-z]?|n\.d\.))\)"
)
_PAREN_GROUP = re.compile(r"\(([^()]*;[^()]*)\)")
_CITE_PART = re.compile(r".*(?:\d{4}[a-z]?|n\.d\.)$")


def _tidy_group(match: re.Match) -> str:
    parts = [part.strip() for part in match.group(1).split(";")]
    if not all(_CITE_PART.match(part) for part in parts):
        return match.group(0)
    unique = sorted(dict.fromkeys(parts), key=str.casefold)
    return "(" + "; ".join(unique) + ")"


def merge_adjacent_citations(text: str) -> str:
    """(A, 2020) (B, 2021) -> (A, 2020; B, 2021), de-duplicated and alphabetised."""
    previous = None
    while previous != text:
        previous = text
        text = _ADJACENT_CITES.sub(lambda m: f"({m.group(1)}; {m.group(2)})", text)
    return _PAREN_GROUP.sub(_tidy_group, text)


def resolve_in_text_citations(text: str, citation_registry: list[dict]) -> str:
    """Replace every [CR-XXX] tag with a proper in-text citation."""
    registry = {
        entry.get("id"): entry
        for entry in citation_registry
        if entry.get("evidence_level") != "none"
    }

    def replace_tag(match: re.Match) -> str:
        entry = registry.get(match.group(1).upper())
        return format_in_text_citation(entry) if entry else "(citation needed)"

    return merge_adjacent_citations(CITATION_TAG.sub(replace_tag, text))


# ------------------------------------------------------------
# Reference list
# ------------------------------------------------------------
def format_apa_reference(entry: dict) -> str:
    """Format one registry entry as an APA-style reference-list entry."""
    authors_list = _split_authors(entry.get("authors", "Unknown"))
    if authors_list:
        apa_authors = []
        for author in authors_list:
            if re.fullmatch(r"[^,]+,\s*(?:[A-Z]\.\s*)+", author):
                apa_authors.append(author)
                continue
            if "," in author:
                surname, given_names = (part.strip() for part in author.split(",", 1))
            else:
                name_parts = author.split()
                surname, given_names = name_parts[-1], " ".join(name_parts[:-1])
            initials = " ".join(f"{part[0]}." for part in given_names.split() if part)
            apa_authors.append(f"{surname}, {initials}".rstrip(", "))
        authors = ", ".join(apa_authors[:-1])
        authors = f"{authors}, & {apa_authors[-1]}" if len(apa_authors) > 1 else apa_authors[0]
    else:
        authors = ""

    year = entry.get("year") or "n.d."
    title = (entry.get("title") or "Untitled").strip().rstrip(".")
    journal = (entry.get("journal") or "").strip().rstrip(".")
    volume = str(entry.get("volume") or "").strip()
    issue = str(entry.get("issue") or "").strip()
    pages = str(entry.get("pages") or "").strip()
    doi = (entry.get("doi") or "").strip()
    url = (entry.get("url") or "").strip()

    pieces = []
    if authors:
        pieces.append(f"{authors} ({year}).")
    else:
        pieces.append(f"{title} ({year}).")
        title = ""
    if title:
        pieces.append(f"{title}.")
    if journal:
        publication = f"*{journal}*"
        if volume:
            publication += f", *{volume}*"
        if issue:
            publication += f"({issue})" if volume else f", {issue}"
        if pages:
            publication += f", {pages}"
        pieces.append(f"{publication}.")
    if doi:
        pieces.append(doi if doi.startswith("http") else f"https://doi.org/{doi}")
    elif url:
        pieces.append(url)
    if entry.get("title_verified") is False:
        pieces.append("[Bibliographic details could not be read from the uploaded file.]")

    return " ".join(piece for piece in pieces if piece)


def build_reference_list(
    citation_registry: list[dict], used_ids: set[str] | None = None
) -> list[str]:
    """Build an alphabetized reference list, optionally limited to used IDs."""
    entries = citation_registry
    if used_ids is not None:
        entries = [entry for entry in entries if entry.get("id") in used_ids]
    entries = [entry for entry in entries if entry.get("evidence_level") != "none"]

    def sort_key(entry: dict) -> str:
        authors = _split_authors(entry.get("authors", ""))
        return _surname(authors[0]).lower() if authors else (entry.get("title") or "").lower()

    return [format_apa_reference(entry) for entry in sorted(entries, key=sort_key)]


def resolve_and_append_references(
    draft_text: str,
    citation_registry: list[dict],
    heading: str = "## References",
    strip_markers: bool = False,
) -> str:
    """Resolve in-text citation tags and append references for cited sources."""
    if (
        not CITATION_TAG.search(draft_text)
        and re.search(r"(?im)^\s*##\s+references\s*$", draft_text)
    ):
        return draft_text

    draft_text = normalize_citation_tags(draft_text)
    draft_text = flag_placeholder_template_syntax(draft_text)
    draft_text = flag_unverified_freeform_citations(draft_text, citation_registry)
    draft_text = collapse_duplicate_citation_markers(draft_text)
    used_ids = {citation_id.upper() for citation_id in CITATION_TAG.findall(draft_text)}
    resolved = resolve_in_text_citations(draft_text, citation_registry)
    if strip_markers:
        resolved, _ = clean_citation_needed_markers(resolved)
    references = build_reference_list(citation_registry, used_ids=used_ids)

    if not references:
        return resolved

    # Blank line between entries so Markdown renders them as separate paragraphs.
    reference_block = "\n\n".join(references)
    return f"{resolved.rstrip()}\n\n{heading}\n\n{reference_block}"


# ------------------------------------------------------------
# Phase 3 & 6: Citation Integrity, Release Gate & Metrics
# ------------------------------------------------------------
_PLACEHOLDER_RELEASE_GATE = re.compile(
    r"\[(?:CITATION\s+NEEDED|TODO|TBD|INSERT[^\]]*|FIGURE:[^\]]*)\]|\b(?:TODO|TBD)\b",
    re.IGNORECASE,
)


def check_citation_integrity(
    draft_text: str,
    citation_registry: list[dict],
    is_resolved: bool = False,
) -> tuple[bool, list[str]]:
    """Fail check if:
    1. Any cited [CR-...] ID has no reference entry in citation_registry.
    2. If is_resolved is True, any CR- string remains in the output text.
    """
    errors: list[str] = []
    registry_ids = {
        entry.get("id", "").upper(): entry
        for entry in citation_registry
        if entry.get("evidence_level") != "none" and entry.get("id")
    }

    raw_ids = [m.upper() for m in CITATION_TAG.findall(draft_text)]
    for cid in set(raw_ids):
        if cid not in registry_ids:
            errors.append(f"Cited ID [{cid}] has no reference entry in citation registry.")

    if is_resolved:
        leaked = re.findall(r"(?:\[CR-\d+|CR-\d{3})", draft_text)
        if leaked:
            errors.append(f"Unresolved CR- string(s) remain in final output: {sorted(set(leaked))}")

    return len(errors) == 0, errors


def validate_release_gate(
    final_text: str,
    citation_registry: list[dict],
    sections: list[dict] | None = None,
    min_sources: int = 3,
    review_list: list[str] | None = None,
    cited_source_ids: set[str] | None = None,
) -> tuple[bool, list[str], dict]:
    """Release Gate (Phase 6):
    Blocks output if there are any placeholders, leaked IDs, an empty reference list,
    or fewer than minimum number of sources.

    Tracks per run:
    - unique_sources
    - share_of_factual_sentences_with_verified_citations
    - claims_sent_to_review_list
    """
    errors: list[str] = []

    # 1. Placeholders
    placeholders = _PLACEHOLDER_RELEASE_GATE.findall(final_text)
    if placeholders:
        errors.append(f"Output blocked: placeholders found in text: {sorted(set(placeholders))}")

    # 2. Leaked IDs
    leaked_ids = re.findall(r"(?:\[CR-\d+|CR-\d{3})", final_text)
    if leaked_ids:
        errors.append(f"Output blocked: leaked CR- tags found in output: {sorted(set(leaked_ids))}")

    # 3. References and unique sources
    has_refs = bool(re.search(r"(?im)^\s*##\s+(?:references|bibliography|works cited)\b", final_text))
    if not has_refs and "## References" not in final_text:
        errors.append("Output blocked: reference list is empty or missing.")

    valid_ids = {
        s.get("id", "").upper()
        for s in citation_registry
        if s.get("evidence_level") != "none" and s.get("id")
    }
    unique_sources = 0
    if cited_source_ids is not None:
        unique_sources = len({source_id.upper() for source_id in cited_source_ids} & valid_ids)
    elif sections:
        section_text_all = "\n".join(s.get("text", "") for s in sections)
        raw_used = set(CITATION_TAG.findall(section_text_all))
        if raw_used:
            unique_sources = len(raw_used)
        else:
            resolved_matches = _RESOLVED_CITATION.findall(section_text_all)
            unique_sources = len(set(resolved_matches))
    if unique_sources == 0:
        raw_used = set(CITATION_TAG.findall(final_text))
        if raw_used:
            unique_sources = len(raw_used)
        else:
            resolved_matches = _RESOLVED_CITATION.findall(final_text)
            unique_sources = len(set(resolved_matches))

    if unique_sources < min_sources:
        errors.append(
            f"Output blocked: fewer than minimum number of sources ({unique_sources} found, minimum {min_sources})."
        )

    # Missing registry entries check
    raw_ids_in_final = set(CITATION_TAG.findall(final_text))
    missing = [cid for cid in raw_ids_in_final if cid.upper() not in valid_ids]
    if missing:
        errors.append(f"Output blocked: cited ID(s) without reference entry: {missing}")

    # 4. Metrics
    sentences = split_prose_sentences(final_text)
    total_factual = 0
    verified_factual = 0
    for s in sentences:
        if not is_meta_or_scope_sentence(s) and len(s.split()) >= _MIN_CLAIM_WORDS:
            total_factual += 1
            if _RESOLVED_CITATION.search(s) or (set(CITATION_TAG.findall(s)) & valid_ids):
                verified_factual += 1

    share_verified = round(verified_factual / total_factual, 3) if total_factual > 0 else 1.0
    review_count = len(review_list or [])

    metrics = {
        "unique_sources": unique_sources,
        "share_of_factual_sentences_with_verified_citations": share_verified,
        "total_factual_sentences": total_factual,
        "verified_factual_sentences": verified_factual,
        "claims_sent_to_review_list": review_count,
        "passed_gate": len(errors) == 0,
    }

    return len(errors) == 0, errors, metrics


# ------------------------------------------------------------
# Phase 5: DOI Resolution Verification
# ------------------------------------------------------------
async def verify_doi_resolves(doi: str, timeout: float = 5.0) -> bool:
    """Verify that a DOI resolves via doi.org."""
    if not doi or not str(doi).strip():
        return False
    clean_doi = str(doi).strip()
    for prefix in ("http://", "https://", "doi.org/", "dx.doi.org/"):
        if clean_doi.lower().startswith(prefix):
            clean_doi = clean_doi[len(prefix):]
    clean_doi = clean_doi.strip()
    if not clean_doi:
        return False

    url = f"https://doi.org/{clean_doi}"
    headers = {"User-Agent": "GenResearch/0.2.0 (mailto:research@genresearch.dev)"}
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            try:
                async with session.head(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status < 400:
                        return True
            except Exception:
                pass
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                return resp.status < 400
    except Exception:
        return False


async def verify_registry_dois(citation_registry: list[dict], timeout: float = 5.0) -> list[dict]:
    """Verify all reference DOIs in citation_registry concurrently."""
    import asyncio

    async def _check(entry: dict) -> dict:
        doi = entry.get("doi")
        if not doi:
            return {**entry, "doi_verified": None}
        resolves = await verify_doi_resolves(doi, timeout=timeout)
        return {**entry, "doi_verified": resolves}

    return await asyncio.gather(*(_check(entry) for entry in citation_registry))