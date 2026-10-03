from services.citation_formatting import (
    build_reference_list,
    format_apa_reference,
    format_in_text_citation,
    flag_unverified_freeform_citations,
    flag_ungrounded_specifics,
    _split_sentences,
    collapse_duplicate_citation_markers,
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


def test_resolve_and_append_references_flags_unverified_freeform_citations():
    result = resolve_and_append_references(
        "Claim (Davies et al., 2020) and verified claim [CR-001].", REGISTRY
    )

    assert "Davies" not in result
    assert "[CITATION NEEDED]" in result
    assert "(Tay et al., 2022)" in result


def test_grounding_gate_allows_supported_specifics_and_flags_invented_case_details():
    evidence = {
        "CR-001": "The study by Insilico Medicine evaluated ISM001 in 2021 and reported 60 percent improvement."
    }
    grounded = flag_ungrounded_specifics(
        "Insilico Medicine evaluated ISM001 in 2021 and reported 60 percent improvement [CR-001].",
        evidence,
        {"CR-001"},
        topic="AI drug discovery",
    )
    invented = flag_ungrounded_specifics(
        "Insilico Medicine evaluated ISM002 in 2022 and reported 92% improvement [CR-001].",
        evidence,
        {"CR-001"},
        topic="AI drug discovery",
    )

    assert "[CITATION NEEDED]" not in grounded
    assert "[CITATION NEEDED]" in invented


def test_grounding_gate_flags_percent_format_mismatch_for_review():
    result = flag_ungrounded_specifics(
        "The study reported 92% improvement [CR-001].",
        {"CR-001": "The study reported 92 percent improvement."},
        {"CR-001"},
    )

    assert "[CITATION NEEDED]" in result


def test_sources_without_evidence_are_not_resolved_or_listed():
    registry = [{"id": "CR-001", "title": "Empty source", "evidence_level": "none"}]

    resolved = resolve_and_append_references("Claim [CR-001].", registry)

    assert "(citation needed)" in resolved
    assert "Empty source" not in resolved


def test_sentence_splitter_preserves_et_al_and_other_abbreviations():
    parts = _split_sentences(
        "Smith et al. demonstrated X. This is also common in the U.S. today."
    )

    assert parts == [
        "Smith et al. demonstrated X.",
        "This is also common in the U.S. today.",
    ]


def test_citing_author_phrase_does_not_trigger_entity_gate():
    result = flag_ungrounded_specifics(
        "Smith et al. demonstrated this in skin cancer detection [CR-001].",
        {"CR-001": "A study on dermatology image classification using convolutional networks."},
        {"CR-001"},
        topic="AI in medicine",
    )

    assert "[CITATION NEEDED]" not in result


def test_unsupported_numbers_remain_flagged_with_valid_citation():
    result = flag_ungrounded_specifics(
        "The study reported 92% improvement [CR-001].",
        {"CR-001": "The study reported 60 percent improvement."},
        {"CR-001"},
    )

    assert "[CITATION NEEDED]" in result


def test_duplicate_citation_needed_markers_collapse():
    spam = "Claim [CITATION NEEDED] [CITATION NEEDED] [CITATION NEEDED]."

    assert collapse_duplicate_citation_markers(spam) == "Claim [CITATION NEEDED]."
    assert collapse_duplicate_citation_markers("Claim [CITATION NEEDED].") == "Claim [CITATION NEEDED]."


def test_reference_resolution_collapses_duplicate_markers():
    resolved = resolve_and_append_references(
        "Claim [CITATION NEEDED] [CITATION NEEDED].", citation_registry=[]
    )

    assert resolved == "Claim [CITATION NEEDED]."
