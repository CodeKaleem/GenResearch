from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PaperItem:
    kind: str
    label: str | None
    caption: str
    page: int | None = None


def extract_items(text: str) -> list[PaperItem]:
    items: list[PaperItem] = []
    pattern = re.compile(r"(?im)^(?:Figure|Fig\.|Table)\s*\d+[.:]?\s*(.*)$")
    for match in pattern.finditer(text):
        kind = "figure" if match.group(0).lower().startswith("figure") or match.group(0).lower().startswith("fig") else "table"
        label = match.group(0).split(" ", 1)[0] if match.group(0) else None
        caption = match.group(1).strip() or match.group(0)
        items.append(PaperItem(kind=kind, label=label, caption=caption, page=None))
    return items
