"""Regression metrics for generated proposal outputs."""
from __future__ import annotations

import re

from models.schemas import ProposalOutput


def numeric_accuracy(output: ProposalOutput, expected_numbers: list[str]) -> float:
    text = "\n".join(section.text for section in output.sections)
    expected = {str(number) for number in expected_numbers}
    if not expected:
        return 1.0
    return sum(number in text for number in expected) / len(expected)


def section_coverage(output: ProposalOutput, required_topics: list[str]) -> float:
    text = "\n".join(section.text.lower() for section in output.sections)
    if not required_topics:
        return 1.0
    return sum(topic.lower() in text for topic in required_topics) / len(required_topics)


def citation_validity(output: ProposalOutput) -> float:
    verdicts = [result.verdict for section in output.sections for result in section.verification]
    if not verdicts:
        return 0.0
    return sum(verdict == "supported" for verdict in verdicts) / len(verdicts)


def quality_report(output: ProposalOutput, required_topics: list[str] | None = None) -> dict:
    """Compute the quality summary from the same verification results."""
    return {
        "citation_validity": citation_validity(output),
        "section_coverage": section_coverage(output, required_topics or []),
        "unsupported_claims": sum(
            result.verdict != "supported"
            for section in output.sections
            for result in section.verification
        ),
        "numeric_mentions": len(re.findall(r"\b\d+(?:\.\d+)?\b", " ".join(s.text for s in output.sections))),
    }