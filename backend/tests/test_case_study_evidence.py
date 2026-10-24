"""Case-study source provenance through retrieval, ingestion, and drafting."""
import asyncio

from services.agents.nodes import source_gathering
from services.agents.nodes.context_build import _select_relevant_sources, context_build_node
from services.agents.nodes.ingestion import ingestion_node
from services.agents.prompts.draft import build_draft_prompt


def test_case_study_query_is_reserved_and_categorized(monkeypatch):
    monkeypatch.setattr(source_gathering.settings, "SCRAPER_ENABLE_CASE_STUDIES", True)

    queries = source_gathering._build_smart_queries(
        "Crop drought resilience",
        {
            "research_questions": [f"How does method {i} affect resilience?" for i in range(4)],
            "key_themes": ["field outcomes", "yield"],
        },
        {"missing": [{"topic": f"gap {i}", "search_query": f"gap query {i}"} for i in range(3)]},
    )

    case_queries = [query for query in queries if query.get("source_category") == "case_study_candidate"]
    assert len(queries) <= source_gathering.MAX_QUERIES
    assert len(case_queries) == 1
    assert case_queries[0]["search_query"] == "Crop drought resilience case study"


def test_ingestion_preserves_case_study_source_category(monkeypatch):
    async def fake_store_chunks_session(**kwargs):
        return 1

    monkeypatch.setattr(
        "services.agents.nodes.ingestion.store_chunks_session", fake_store_chunks_session
    )
    result = asyncio.run(
        ingestion_node({
            "session_id": "session-1",
            "scraped_sources": [{
                "title": "A drought-resilience field study",
                "authors": "A. Author",
                "year": 2024,
                "abstract_snippet": "A sufficiently detailed abstract about crop drought resilience.",
                "source_api": "crossref",
                "source_category": "case_study_candidate",
            }],
        })
    )

    assert result["citation_registry"][0]["source_category"] == "case_study_candidate"


def test_draft_prompt_labels_case_study_candidate_and_limits_claims():
    prompt = build_draft_prompt(
        topic="Crop drought resilience",
        outline={"sections": [{"name": "Case Studies"}]},
        citation_registry=[{
            "id": "CR-001",
            "title": "A drought-resilience field study",
            "authors": "A. Author",
            "year": 2024,
            "source_category": "case_study_candidate",
        }],
        rag_context="The study reports observations from one field site.",
    )

    assert "[case-study candidate]" in prompt
    assert "only when its retrieved source text confirms" in prompt


def test_case_study_section_prefers_relevant_case_study_candidates():
    registry = [
        {
            "id": "CR-001",
            "title": "General crop performance overview",
            "abstract_snippet": "An overview of crop yield under multiple conditions.",
        },
        {
            "id": "CR-002",
            "title": "Crop drought resilience field case study",
            "abstract_snippet": "A field case study reports crop yields during drought.",
            "source_category": "case_study_candidate",
        },
    ]

    selected = _select_relevant_sources(
        "Case Studies",
        "Compare crop drought resilience field evidence.",
        registry,
    )

    assert selected[0]["id"] == "CR-002"


def test_context_build_adds_case_study_evidence_section_when_sources_exist():
    result = asyncio.run(
        context_build_node({
            "topic": "Crop drought resilience",
            "outline": {"sections": [{"name": "Introduction", "guidance": "Context"}]},
            "citation_registry": [{
                "id": "CR-001",
                "title": "Crop drought field case study",
                "abstract_snippet": "A field case study reports crop resilience during drought.",
                "source_category": "case_study_candidate",
                "evidence_level": "abstract",
            }],
        })
    )

    case_section = result["outline"]["sections"][-1]
    case_context = result["section_contexts"][-1]
    assert case_section["name"] == "Case Study Evidence"
    assert case_context["assigned_sources"][0]["id"] == "CR-001"