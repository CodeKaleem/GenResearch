from ingestion.quality_gate import check_relevance_preview


def test_quality_gate_matches_topic_terms():
    result = check_relevance_preview("Privacy in healthcare", "This paper studies privacy risks.", "healthcare privacy")
    assert result["relevant"] is True


def test_quality_gate_rejects_unrelated_preview():
    result = check_relevance_preview("Astronomy", "Stars and galaxies.", "healthcare privacy")
    assert result["relevant"] is False