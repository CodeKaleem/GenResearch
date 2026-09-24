from models.schemas import GeneratedSection, ProposalOutput, VerificationResult
from eval.scorers import citation_validity, numeric_accuracy, section_coverage


def test_quality_scorers_use_typed_output():
    output = ProposalOutput(
        topic="Study",
        sections=[GeneratedSection(
            section_name="results",
            text="The study covered 100 papers about privacy.",
            verification=[VerificationResult(claim_id="c1", verdict="supported")],
        )],
    )
    assert numeric_accuracy(output, ["100"]) == 1.0
    assert section_coverage(output, ["privacy"]) == 1.0
    assert citation_validity(output) == 1.0