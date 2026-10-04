"""Integration coverage for section-level evidence retrieval."""
import asyncio

from config import settings
from database import chroma_client
from services import chroma_service, rag_service
from services.agents.nodes import context_build as context_module
from services.agents.nodes import draft as draft_module


def test_synthesis_sections_receive_sources_with_retrievable_chunks(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "CHROMA_PERSIST_PATH", str(tmp_path))
    monkeypatch.setattr(chroma_client, "_client", None)

    async def fake_embed_texts(texts):
        return [[1.0, 0.0] for _ in texts]

    async def fake_embed_single(text):
        return [1.0, 0.0]

    monkeypatch.setattr(chroma_service, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(rag_service, "embed_single", fake_embed_single)

    session_id = "section-evidence-test"
    source_ids = ["CR-001", "CR-002", "CR-003"]
    chunks = [
        "AI research source one provides evidence for synthesis sections.",
        "AI research source two provides evidence for synthesis sections.",
        "AI research source three provides evidence for synthesis sections.",
    ]
    registry = [
        {
            "id": source_id,
            "title": f"Study {index}",
            "abstract_snippet": chunk,
            "evidence_level": "full_text",
        }
        for index, (source_id, chunk) in enumerate(zip(source_ids, chunks), 1)
    ]

    async def seed_collection():
        await chroma_service.store_chunks_session(
            session_id=session_id,
            source_id=source_ids[0],
            chunks=[chunks[0]],
            title="Study 1",
        )
        await chroma_service.store_chunks_session(
            session_id=session_id,
            source_id=source_ids[1],
            chunks=[chunks[1]],
            title="Study 2",
        )
        await chroma_service.store_chunks_session(
            session_id=session_id,
            source_id=source_ids[2],
            chunks=[chunks[2]],
            title="Study 3",
        )

    asyncio.run(seed_collection())
    outline = {
        "sections": [
            {"name": name, "guidance": "Organize the argument clearly."}
            for name in ["Abstract", "Introduction", "Literature Review", "Methodology", "Discussion", "Conclusion"]
        ]
    }
    base_state = {
        "topic": "AI research",
        "session_id": session_id,
        "outline": outline,
        "citation_registry": registry,
    }

    context_result = asyncio.run(context_module.context_build_node(base_state))
    assigned_by_section = {
        context["section_name"]: {source["id"] for source in context["assigned_sources"]}
        for context in context_result["section_contexts"]
    }

    captured_evidence = {}

    async def fake_llm(**kwargs):
        return "The evidence supports synthesis [CR-001]."

    async def capture_verification(section, excerpt_map, session_id="", topic=""):
        captured_evidence[section.section_name] = set(excerpt_map)
        return section

    monkeypatch.setattr(draft_module, "call_llm", fake_llm)
    monkeypatch.setattr(draft_module, "verify_section", capture_verification)
    asyncio.run(
        draft_module.draft_node(
            {**base_state, **context_result}
        )
    )

    assert all(assigned_by_section.values())
    for section_name, assigned_ids in assigned_by_section.items():
        assert assigned_ids <= captured_evidence[section_name]

    restricted_hits = asyncio.run(
        rag_service.semantic_search_session(
            session_id=session_id,
            query="AI research",
            top_k=8,
            source_ids=["CR-002"],
        )
    )
    assert {hit["source_id"] for hit in restricted_hits} == {"CR-002"}