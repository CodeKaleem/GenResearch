from models.schemas import GeneratedSection
from services.agents.composer_agent import find_redundant_pairs, lint_citations


def test_redundant_sentence_detection():
    text = "This study examines privacy risks in healthcare datasets and evaluates explainable methods."
    pairs = find_redundant_pairs([
        GeneratedSection(section_name="introduction", text=text),
        GeneratedSection(section_name="discussion", text=text),
    ])
    assert len(pairs) == 1


def test_citation_lint_checks_both_directions():
    errors = lint_citations("Claim [CR-001].", [{"id": "CR-001"}, {"id": "CR-002"}])
    assert errors == ["Registry entry CR-002 is not cited"]