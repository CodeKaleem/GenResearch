from __future__ import annotations

import pytest

from services.doc_structure.references import (
    ReferenceEntry,
    find_reference_section,
    parse_reference_entries,
    parse_reference_entries_from_pages,
)
from services.agents.citation_agent import _format_reference_entry, _clean_ref_string


def test_find_reference_section_multiline_and_multipage():
    pages = [
        "Title of Paper\nAbstract\nIntroduction...",
        "Methods and Results\nDiscussion...",
        "Conclusion\nReferences\n1. Author A (2020) Paper A. Journal 1\n2. Author B (2021) Paper B. Journal 2",
        "3. Author C (2022) Paper C. Journal 3\n4. Author D (2023) Paper D. Journal 4",
    ]
    start_page, ref_text = find_reference_section(pages)
    assert start_page == 3
    # Check that both page 3 and page 4 are collected
    assert "1. Author A" in ref_text
    assert "4. Author D" in ref_text


def test_reference_sequence_tracking_filters_false_markers():
    text = """
    References
    1. First Author (2018) Intro to AI. AI Journal
    2. Second Author (2019) Deep Learning. DL Journal
    591. Continuing details on line 591
    3. Third Author (2020) Transformers. NLP Journal
    2015. Historical footnote 2015
    4. Fourth Author (2021) Graph Nets. Graph Journal
    """
    bundle = parse_reference_entries(text)
    assert bundle.reference_count == 4
    nums = [e.ref_number for e in bundle.entries]
    assert nums == [1, 2, 3, 4]


def test_doi_newline_unwrapping():
    text = """
    References
    1. Christopher MB (1999) Bayesian PCA. Neural Comput. https://doi.org/10.1162/
    089976698300017737
    """
    bundle = parse_reference_entries(text)
    assert len(bundle.entries) == 1
    assert bundle.entries[0].doi == "10.1162/089976698300017737"


def test_citation_agent_formatting_styles():
    entry = ReferenceEntry(
        ref_number=1,
        raw="1. Kaul V, Enslin S, Gross SA (2020) The history of artificial intelligence in medicine. Gastrointest Endosc",
        doi="10.1016/j.gie.2020.04.057",
    )

    apa = _format_reference_entry(entry, 1, "apa")
    ieee = _format_reference_entry(entry, 1, "ieee")

    assert apa.startswith("1. Kaul V")
    assert "https://doi.org/10.1016/j.gie.2020.04.057" in apa
    assert ieee.startswith("[1] Kaul V")
    assert "https://doi.org/10.1016/j.gie.2020.04.057" in ieee
