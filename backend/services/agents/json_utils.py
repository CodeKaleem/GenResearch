"""Utilities for parsing structured responses from local LLMs."""
from __future__ import annotations

import json


def parse_llm_json(raw: str) -> dict | None:
    """Return the first balanced JSON object in a model reply, or ``None``."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None

    for start, character in enumerate(text):
        if character != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for end in range(start, len(text)):
            current = text[end]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:end + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        return value
                    break
    return None


def coerce_score(value: object, *, percentage: bool = False) -> float | None:
    """Convert numeric model scores safely; normalize percentages when requested."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if percentage and score > 1:
        score /= 100
    return score