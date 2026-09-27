"""Regression tests for draft-content and unresolved-figure safeguards."""
from services.agents.prompts.draft import (
    DRAFT_SYSTEM,
    FEW_SHOT_EXEMPLARS,
    build_draft_prompt,
)

OLD_EXEMPLAR_FINGERPRINTS = [
    "Smith et al",
    "Chen and Wang",
    "Park et al",
    "knowledge distillation",
    "encoder-only architectures",
    "multi-modal transformers",
    "[CR-005]",
    "[CR-006]",
    "[CR-007]",
    "[CR-008]",
]


def test_exemplars_do_not_contain_old_fabricated_content():
    for fingerprint in OLD_EXEMPLAR_FINGERPRINTS:
        assert fingerprint not in FEW_SHOT_EXEMPLARS


def test_exemplars_are_schematic_templates():
    assert "[Author" in FEW_SHOT_EXEMPLARS
    assert "[a real finding" in FEW_SHOT_EXEMPLARS


def test_prompt_forbids_self_written_references_duplicate_headings_and_figures():
    assert "References" in DRAFT_SYSTEM and "do not" in DRAFT_SYSTEM.lower()
    assert "repeat the section title" in DRAFT_SYSTEM.lower()
    assert "[FIGURE:" in DRAFT_SYSTEM


def test_prompt_repeats_guardrails_after_the_exemplars():
    prompt = build_draft_prompt(
        topic="test topic",
        outline={"sections": [{"name": "Introduction"}]},
        citation_registry=[],
        rag_context="thin context",
    )
    assert prompt.find("Final reminders") > prompt.find("EXEMPLAR 1")
