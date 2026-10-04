import asyncio

from models.schemas import GeneratedSection
from services.agents import verification_agent
from services.agents.verification_agent import extract_claims_from_text


def test_claims_capture_evidence_tags():
    claims = extract_claims_from_text(
        "The study evaluated 100 papers [E1]. It used a mixed-method design [E2].",
        "results",
    )

    assert len(claims) == 2
    assert claims[0].cited_chunk_ids == ["E1"]
    assert claims[1].cited_chunk_ids == ["E2"]


def test_claim_without_evidence_is_retained_for_rejection():
    claims = extract_claims_from_text("The method improves reliability significantly.", "results")

    assert claims[0].cited_chunk_ids == []


def test_claim_extraction_keeps_et_al_and_author_initials_together():
    claims = extract_claims_from_text(
        "A. B. Smith and Rajpurkar et al. reported improved diagnostic accuracy [CR-001].",
        "results",
    )

    assert len(claims) == 1
    assert "Rajpurkar et al." in claims[0].text
    assert claims[0].cited_chunk_ids == ["CR-001"]


def test_invented_drug_claim_is_removed_and_recorded(monkeypatch):
    monkeypatch.setattr(verification_agent.tracking, "save_generated_claim", lambda **kwargs: None)
    section = GeneratedSection(
        section_name="Results",
        text=(
            "The trial evaluated the invented drug Remdesivir for this condition. "
            "The broader research question remains important."
        ),
    )

    result = asyncio.run(verification_agent.verify_section(section, {}, topic="clinical AI"))

    assert "Remdesivir" not in result.text
    assert result.removed_claims == [
        "The trial evaluated the invented drug Remdesivir for this condition."
    ]


def test_generic_uncited_sentence_is_kept_with_one_inline_marker(monkeypatch):
    monkeypatch.setattr(verification_agent.tracking, "save_generated_claim", lambda **kwargs: None)
    section = GeneratedSection(
        section_name="Introduction",
        text="This section introduces the general research problem.",
    )

    result = asyncio.run(verification_agent.verify_section(section, {}, topic="research"))

    assert result.text == "This section introduces the general research problem [CITATION NEEDED]."
    assert result.text.count("[CITATION NEEDED]") == 1


def test_verifier_exception_becomes_unsupported_result(monkeypatch):
    monkeypatch.setattr(verification_agent.tracking, "save_generated_claim", lambda **kwargs: None)

    async def fail_call_llm(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(verification_agent, "call_llm", fail_call_llm)
    section = GeneratedSection(
        section_name="Results",
        text="The cited study evaluated a diagnostic model [CR-001].",
    )

    result = asyncio.run(
        verification_agent.verify_section(section, {"CR-001": "A diagnostic study."})
    )

    assert result.verified
    assert result.verification[0].verdict == "unsupported"
    assert "verifier error" in result.verification[0].discrepancy


def test_removing_every_unsupported_claim_preserves_section_text(monkeypatch):
    monkeypatch.setattr(verification_agent.tracking, "save_generated_claim", lambda **kwargs: None)
    section = GeneratedSection(
        section_name="Case Study",
        text=(
            "The trial used the invented drug Remdesivir. "
            "The study enrolled 640 participants."
        ),
    )

    result = asyncio.run(verification_agent.verify_section(section, {}))

    assert result.text == section.text
    assert result.under_evidenced
    assert result.removed_claims == []


def test_completion_guide_lists_removed_claims_and_under_evidenced_sections():
    from services.report_store import build_completion_guide_text

    guide = build_completion_guide_text({
        "topic": "test",
        "generated_sections": [{
            "section_name": "Case Study",
            "under_evidenced": True,
            "removed_claims": ["The trial used Remdesivir."],
        }],
    })

    assert "Case Study" in guide
    assert "under-evidenced" in guide.lower()
    assert "The trial used Remdesivir." in guide