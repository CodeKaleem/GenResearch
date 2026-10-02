import asyncio

from models.schemas import GeneratedSection
from services.agents.pipeline_graph import build_pipeline_graph
from services.agents.nodes.context_build import context_build_node
from services.agents.nodes import draft as draft_module
from services.agents.nodes.draft import _format_section_context_block
from services.agents.state import FigureSlot, ProposalState, SectionContext
from services.citation_formatting import flag_unverified_freeform_citations
from services.pdf_renderer import APAPDFRenderer, render_markdown_to_pdf


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
    # The registry entry's title must share real vocabulary with the section
    # (here: "example") since context_build_node now assigns sources by
    # relevance rather than handing every section the same top-N slice.
    result = asyncio.run(
        context_build_node(
            {
                "outline": {
                    "sections": [
                        {"name": "Introduction", "guidance": "Introduce the example paper's topic."}
                    ]
                },
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


def test_context_build_keeps_sources_and_claims_empty_without_registry_entries():
    result = asyncio.run(
        context_build_node(
            {
                "outline": {"sections": [{"name": "Methodology"}]},
                "citation_registry": [],
            }
        )
    )

    context = result["section_contexts"][0]
    assert context["assigned_sources"] == []
    assert context["claims"] == []
    assert result["figure_slots"][0]["source_id"] is None


def test_draft_node_does_not_inject_figures_and_flags_freeform_citations(monkeypatch):
    async def fake_search(**kwargs):
        return []

    async def fake_llm(**kwargs):
        return "Section evidence (Davies et al., 2020)."

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

    assert "Davies" not in result["draft_text"]
    assert "[CITATION NEEDED]" in result["draft_text"]
    assert "[[FIGURE:" not in result["draft_text"]
    GeneratedSection.model_validate(result["generated_sections"][0])


def test_section_context_block_formats_real_sources_and_empty_sources():
    block = _format_section_context_block(
        {
            "assigned_sources": [{"id": "CR-001", "title": "Real paper"}],
            "claims": [{"text": "A supported point."}],
            "narrative_prompt": "Write carefully.",
            "section_goal": "Explain the method.",
        }
    )
    empty_block = _format_section_context_block(
        {"assigned_sources": [], "claims": []}
    )

    assert "[CR-001] Real paper" in block
    assert "{'id':" not in block
    assert "No real source is available" in empty_block
    assert "[[FIGURE:id]]" not in block + empty_block


def test_freeform_citations_are_flagged_and_registry_tags_are_preserved():
    cleaned = flag_unverified_freeform_citations(
        "Unverified (Davies et al., 2020), but verified [CR-001]."
    )

    assert "Davies" not in cleaned
    assert "[CITATION NEEDED]" in cleaned
    assert "[CR-001]" in cleaned


def test_pdf_renderer_treats_h4_as_a_heading(monkeypatch):
    rendered_headings = []
    original_write_heading = APAPDFRenderer.write_heading

    def record_heading(self, text, level):
        rendered_headings.append((text, level))
        return original_write_heading(self, text, level)

    monkeypatch.setattr(APAPDFRenderer, "write_heading", record_heading)
    pdf_bytes = render_markdown_to_pdf(
        "## Methodology\n\n#### Data Collection\n\nSome text.", title="test"
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert ("Data Collection", 3) in rendered_headings
