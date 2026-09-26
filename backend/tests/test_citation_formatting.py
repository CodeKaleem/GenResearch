from services.citation_formatting import (
    build_reference_list,
    format_apa_reference,
    format_in_text_citation,
    resolve_and_append_references,
    resolve_in_text_citations,
)

REGISTRY = [
    {
        "id": "CR-001",
        "title": "Efficient Transformers: A Survey",
        "authors": "Tay, Y., Dehghani, M., Bahri, D.",
        "year": 2022,
        "doi": "10.1145/3530811",
    },
    {
        "id": "CR-002",
        "title": "Attention Is All You Need",
        "authors": "Vaswani, A., Shazeer, N.",
        "year": 2017,
        "url": "https://arxiv.org/abs/1706.03762",
    },
    {
        "id": "CR-003",
        "title": "A Solo-Authored Paper",
        "authors": "Kim, S.",
        "year": 2019,
        "url": "https://example.org/kim",
    },
    {
        "id": "CR-004",
        "title": "Untitled Origin Dataset Report",
        "authors": "Unknown",
        "year": None,
        "url": "https://example.org/report",
    },
]


def test_three_plus_authors_becomes_et_al():
    assert format_in_text_citation(REGISTRY[0]) == "(Tay et al., 2022)"


def test_two_authors_uses_ampersand():
    assert format_in_text_citation(REGISTRY[1]) == "(Vaswani & Shazeer, 2017)"


def test_single_author():
    assert format_in_text_citation(REGISTRY[2]) == "(Kim, 2019)"


def test_unknown_author_falls_back_to_title():
    result = format_in_text_citation(REGISTRY[3])
    assert "n.d." in result
    assert "Untitled Origin Dataset Report" in result


def test_author_units_with_periods_are_not_split_on_every_comma():
    ref = format_apa_reference(REGISTRY[0])
    assert ref.startswith("Tay, Y., Dehghani, M., & Bahri, D.")


def test_resolve_in_text_citations_replaces_all_tags():
    text = "Some claim [CR-001] and another [CR-002]."
    resolved = resolve_in_text_citations(text, REGISTRY)
    assert "[CR-001]" not in resolved
    assert "[CR-002]" not in resolved
    assert "(Tay et al., 2022)" in resolved
    assert "(Vaswani & Shazeer, 2017)" in resolved


def test_unknown_tag_does_not_invent_a_citation():
    text = "A dangling reference [CR-999]."
    resolved = resolve_in_text_citations(text, REGISTRY)
    assert "(citation needed)" in resolved
    assert "CR-999" not in resolved


def test_reference_list_only_includes_cited_sources():
    refs = build_reference_list(REGISTRY, used_ids={"CR-001"})
    assert len(refs) == 1
    assert "Efficient Transformers" in refs[0]


def test_reference_list_is_alphabetized_by_surname():
    used = {"CR-001", "CR-002", "CR-003"}
    refs = build_reference_list(REGISTRY, used_ids=used)
    surnames_order = [reference.split(",")[0] for reference in refs]
    assert surnames_order == sorted(surnames_order, key=str.lower)


def test_resolve_and_append_references_appends_only_cited_sources():
    draft = "Intro text [CR-001]. Unused source CR-002 is never tagged here."
    result = resolve_and_append_references(draft, REGISTRY)
    assert "## References" in result
    assert "Tay, Y." in result
    assert "Vaswani" not in result


def test_resolve_and_append_references_noop_when_nothing_cited():
    draft = "No citations in this text at all."
    result = resolve_and_append_references(draft, REGISTRY)
    assert "## References" not in result
    assert result == draft
