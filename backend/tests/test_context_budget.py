from models.schemas import RetrievedChunk
from services.context_budget import fit_to_budget


def test_context_budget_prefers_high_score_chunks():
    chunks = [
        RetrievedChunk(chunk_id="low", paper_id="p", text="low score", score=0.1, chunk_index=0),
        RetrievedChunk(chunk_id="high", paper_id="p", text="high score", score=0.9, chunk_index=1),
    ]
    assert fit_to_budget(chunks, 2)[0].chunk_id == "high"