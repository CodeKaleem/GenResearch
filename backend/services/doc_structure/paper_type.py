from __future__ import annotations

import re


def classify_paper_type(title: str, abstract: str = "") -> str:
    text = f"{title} {abstract}".lower()
    if re.search(r"survey|review|overview|systematic", text):
        return "survey"
    if re.search(r"we propose|experiments|dataset|results show|evaluation", text):
        return "empirical"
    return "unknown"
