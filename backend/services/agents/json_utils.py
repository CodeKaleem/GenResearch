"""Utilities for parsing structured responses from local LLMs."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _clean_json_candidate(text: str) -> str:
    """Strip wrappers, thinking blocks, markdown fences, and fix common LLM JSON syntax quirks."""
    if not text:
        return ""
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    # Strip thinking blocks (<think>...</think>)
    text = re.sub(
        r"<(?:think|thought|thinking)>[\s\S]*?(?:</(?:think|thought|thinking)>|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Strip untagged leading preamble ending in </think>
    text = re.sub(
        r"^[\s\S]*?</(?:think|thought|thinking)>\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Python constants to JSON equivalents
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text.strip()


def _repair_truncated_json(text: str) -> str:
    """Repair a JSON string that was truncated mid-generation (e.g., token limit reached)."""
    in_string = False
    escaped = False
    stack: list[str] = []

    for c in text:
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue

        if c == '"':
            in_string = True
        elif c in "{[":
            stack.append("}" if c == "{" else "]")
        elif c in "}]":
            if stack and stack[-1] == c:
                stack.pop()

    repaired = text
    if in_string:
        repaired += '"'

    # Remove dangling key/comma at the cut point
    repaired = re.sub(r",\s*$", "", repaired.strip())
    repaired = re.sub(r":\s*$", ': ""', repaired.strip())
    repaired = re.sub(r",\s*$", "", repaired.strip())

    while stack:
        repaired += stack.pop()

    # Clean any newly exposed trailing commas
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    return repaired


def parse_llm_json(raw: str) -> dict | None:
    """Return a parsed JSON dictionary from a model reply, or None.

    Resilient to:
    - Markdown code blocks (```json ... ```)
    - Chain-of-thought tokens / thinking tags
    - Trailing commas before closing brackets/braces
    - Python literals (True, False, None)
    - Unescaped newlines in strings
    - Truncated output caused by max_tokens limits
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None

    cleaned = _clean_json_candidate(text)

    # 1. Try direct parse of cleaned text
    try:
        val = json.loads(cleaned, strict=False)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    # 2. Locate outermost balanced object '{ ... }'
    first_brace = cleaned.find("{")
    if first_brace >= 0:
        depth = 0
        in_string = False
        escaped = False
        start = first_brace
        outer_end = -1

        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
                continue
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    outer_end = i
                    break

        if outer_end > start:
            candidate = _clean_json_candidate(cleaned[start:outer_end + 1])
            try:
                val = json.loads(candidate, strict=False)
                if isinstance(val, dict):
                    return val
            except Exception:
                pass

        # 3. If depth > 0, the output was truncated while generating the JSON object!
        if depth > 0:
            truncated_candidate = cleaned[start:]
            repaired = _repair_truncated_json(truncated_candidate)
            try:
                val = json.loads(repaired, strict=False)
                if isinstance(val, dict) and val:
                    logger.info("parse_llm_json_recovered_truncated_object", extra={"keys": list(val.keys())})
                    return val
            except Exception:
                pass

    # 4. Fallback: Search for any balanced JSON object inside the text
    for start in range(len(cleaned)):
        if cleaned[start] != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for end in range(start, len(cleaned)):
            c = cleaned[end]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
                continue
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    sub = _clean_json_candidate(cleaned[start:end + 1])
                    try:
                        val = json.loads(sub, strict=False)
                        if isinstance(val, dict):
                            return val
                    except Exception:
                        pass
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