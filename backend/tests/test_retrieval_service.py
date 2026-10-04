import asyncio

from services import rag_service
from services.retrieval_service import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_prefers_consistent_results():
    merged = reciprocal_rank_fusion([
        [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        [{"id": "b", "text": "B"}, {"id": "c", "text": "C"}],
    ])

    assert [item["id"] for item in merged] == ["b", "a", "c"]


def test_semantic_search_exposes_chunk_provenance_at_top_level(monkeypatch):
    class FakeCollection:
        def count(self):
            return 1

        def query(self, **kwargs):
            return {
                "ids": [["stored-chunk-id"]],
                "documents": [["Evidence text"]],
                "metadatas": [[{
                    "paper_id": "paper-1",
                    "title": "Example paper",
                    "chunk_id": "metadata-chunk-id",
                    "chunk_index": 2,
                    "page": 7,
                }]],
                "distances": [[0.1]],
            }

    async def fake_embed_single(query):
        return [1.0, 0.0]

    monkeypatch.setattr(rag_service, "embed_single", fake_embed_single)
    monkeypatch.setattr(rag_service, "get_user_collection", lambda user_id: FakeCollection())

    hits = asyncio.run(rag_service.semantic_search("user-1", "evidence"))

    assert hits[0]["page"] == 7
    assert hits[0]["chunk_id"] == "metadata-chunk-id"