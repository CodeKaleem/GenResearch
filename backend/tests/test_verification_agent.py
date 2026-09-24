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