"""Regression coverage for preferring full uploaded source text to snippets."""
import asyncio
from unittest.mock import AsyncMock, patch

from services.agents.nodes.ingestion import ingestion_node


def test_ingestion_prefers_full_content_over_snippet():
    long_body = "Findings from the study. " * 200
    state = {
        "session_id": "test-session",
        "user_provided_sources": [
            {
                "id": "paper-1",
                "title": "A Long Uploaded Paper",
                "authors": "Doe, J.",
                "year": 2023,
                "content": long_body,
                "abstract_snippet": long_body[:1000],
            }
        ],
        "scraped_sources": [],
        "source_quality_results": {},
    }

    captured = {}

    async def fake_store_chunks_session(session_id, source_id, chunks, title, tag):
        captured["chunks"] = chunks
        return len(chunks)

    with patch(
        "services.agents.nodes.ingestion.store_chunks_session",
        new=AsyncMock(side_effect=fake_store_chunks_session),
    ):
        asyncio.run(ingestion_node(state))

    reconstructed = "".join(captured["chunks"])
    assert len(reconstructed) > 1000
    assert long_body.strip()[-50:] in reconstructed
