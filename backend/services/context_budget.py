"""Defensive context budgeting for retrieval and composition prompts."""
from __future__ import annotations

from models.schemas import RetrievedChunk


def fit_to_budget(chunks: list[RetrievedChunk], budget_tokens: int) -> list[RetrievedChunk]:
    """Keep highest-scored chunks until an approximate token budget is full."""
    if budget_tokens <= 0:
        return []
    total = 0
    selected: list[RetrievedChunk] = []
    for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
        token_estimate = max(1, len(chunk.text.split()))
        if total + token_estimate > budget_tokens:
            continue
        selected.append(chunk)
        total += token_estimate
    return selected