import re
import unicodedata

LIGATURE_FIXES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}

_ACCENT_MAP = {
    "`": "̀",
    "'": "́",
    "´": "́",
    "^": "̂",
    "~": "̃",
    '"': "̈",
    "ˇ": "̌",
    "˘": "̆",
    "¸": "̧",
    "¯": "̄",
    "˚": "̊",
}


def recompose_accents(text: str) -> str:
    """Convert spacing accents like 'R´ios' or 'Catal`a' into composed characters."""
    text = unicodedata.normalize("NFKC", text)
    for accent_char, combining in _ACCENT_MAP.items():
        text = re.sub(
            rf"([A-Za-z]){re.escape(accent_char)}([A-Za-z])",
            rf"\1{unicodedata.normalize('NFC', f'\2{combining}')}",
            text,
        )
    return text


def clean_text(text: str) -> str:
    """Normalize common PDF artifacts without rewriting document content."""
    text = text.replace("\u00ad", "").replace("\u200b", "").replace("\ufeff", "")
    for source, replacement in LIGATURE_FIXES.items():
        text = text.replace(source, replacement)
    text = recompose_accents(text)
    text = re.sub(r"-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()