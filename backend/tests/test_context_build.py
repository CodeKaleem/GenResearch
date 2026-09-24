import asyncio

from models.schemas import GeneratedSection
from services.agents.pipeline_graph import build_pipeline_graph
from services.agents.nodes.context_build import context_build_node
from services.agents.nodes import draft as draft_module
from services.agents.state import FigureSlot, ProposalState, SectionContext


def test_section_context_contract_exists():
    figure: FigureSlot = {
        "id": "figure-1",
        "section_name": "Results and Discussion",
        "kind": "figure",
        "caption": "Study workflow summary",
        "reason": "Placeholder for later rendering",
    }
    section: SectionContext = {
        "section_name": "Results and Discussion",
        "section_goal": "Summarize findings and explain their meaning.",
        "assigned_sources": [{"id": "source-1", "title": "Example paper"}],
        "claims": [{"claim_id": "claim-1", "text": "Findings show improvement.", "source_id": "source-1"}],
        "figure_slots": [figure],
        "narrative_prompt": "Discuss the key findings with evidence.",
    }

    state: ProposalState = {
        "section_contexts": [section],
        "figure_slots": [figure],
    }

    assert state["section_contexts"][0]["section_name"] == "Results and Discussion"
    assert state["figure_slots"][0]["id"] == "figure-1"


def test_pipeline_graph_contains_context_build_node():
    graph = build_pipeline_graph()
    assert "context_build" in graph.nodes


def test_context_claims_match_generated_section_schema():
    result = asyncio.run(
        context_build_node(
            {
                "outline": {"sections": [{"name": "Introduction"}]},
                "citation_registry": [{"id": "CR-001", "title": "Example paper"}],
            }
        )
    )

    section = result["section_contexts"][0]
    generated = GeneratedSection(
        section_name=section["section_name"],
        text="Draft text [[FIGURE:figure-1]]",
        claims=section["claims"],
    )

    assert generated.claims[0].section == "Introduction"


def test_draft_node_emits_one_registered_figure_placeholder(monkeypatch):
    async def fake_search(**kwargs):
        return []

    async def fake_llm(**kwargs):
        return "Section evidence."

    monkeypatch.setattr(draft_module, "semantic_search_session", fake_search)
    monkeypatch.setattr(draft_module, "call_llm", fake_llm)

    result = asyncio.run(
        draft_module.draft_node(
            {
                "topic": "AI in healthcare",
                "outline": {"sections": [{"name": "Introduction"}]},
                "section_contexts": [
                    {
                        "section_name": "Introduction",
                        "section_goal": "Set the context.",
                        "assigned_sources": [],
                        "claims": [],
                        "figure_slots": [],
                        "narrative_prompt": "Introduce the topic.",
                    }
                ],
                "figure_slots": [
                    {"id": "figure-1", "section_name": "Introduction"}
                ],
            }
        )
    )

    assert result["draft_text"].count("[[FIGURE:figure-1]]") == 1
    GeneratedSection.model_validate(result["generated_sections"][0])
