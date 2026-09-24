from services.retrieval_service import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_prefers_consistent_results():
    merged = reciprocal_rank_fusion([
        [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        [{"id": "b", "text": "B"}, {"id": "c", "text": "C"}],
    ])

    assert [item["id"] for item in merged] == ["b", "a", "c"]