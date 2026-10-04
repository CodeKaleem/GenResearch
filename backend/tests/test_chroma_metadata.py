"""Regression coverage for Chroma-safe structured chunk metadata."""
import asyncio
import json

from config import settings
from database import chroma_client
from models.schemas import ChunkMetadata
from services import chroma_service
from services.retrieval_service import _as_retrieved_chunk


def test_structured_metadata_stores_and_round_trips_through_chroma(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "CHROMA_PERSIST_PATH", str(tmp_path))
    monkeypatch.setattr(chroma_client, "_client", None)

    async def fake_embed_texts(texts):
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(chroma_service, "embed_texts", fake_embed_texts)
    chunks = [
        (
            ChunkMetadata(
                chunk_id="plain-chunk",
                paper_id="paper-1",
                title="Metadata defaults",
                chunk_index=0,
            ),
            "Plain structured content.",
        ),
        (
            ChunkMetadata(
                chunk_id="table-chunk",
                paper_id="paper-1",
                title="Metadata table",
                authors=["Alice Author", "Bob Writer"],
                chunk_index=1,
                page=4,
                is_table=True,
                table_data={"rows": [["Measure", "Value"], ["Accuracy", "92%"]]},
            ),
            "Table content.",
        ),
    ]

    stored = asyncio.run(
        chroma_service.store_structured_chunks(
            user_id="user-1",
            chunks=chunks,
            collection_name="research",
        )
    )
    assert stored == 2

    collection = chroma_client.get_user_collection("user-1")
    result = collection.get(
        ids=["plain-chunk", "table-chunk"],
        include=["documents", "metadatas"],
    )
    converted = {
        chunk.chunk_id: chunk
        for chunk in (
            _as_retrieved_chunk(
                {
                    "id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                },
                score=0.9,
            )
            for chunk_id, text, metadata in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        )
    }

    assert converted["plain-chunk"].authors == []
    assert converted["plain-chunk"].table_data is None
    assert converted["table-chunk"].authors == ["Alice Author", "Bob Writer"]
    assert converted["table-chunk"].page == 4
    assert converted["table-chunk"].table_data == {
        "rows": [["Measure", "Value"], ["Accuracy", "92%"]]
    }
    assert json.loads(result["metadatas"][1]["table_data"]) == converted["table-chunk"].table_data