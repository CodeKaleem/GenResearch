import asyncio

from models.schemas import GeneratedSection
from services.agents.pipeline_graph import build_pipeline_graph
from services.agents.nodes import context_build as context_module
from services.agents.nodes.context_build import context_build_node
from services.agents.nodes import draft as draft_module
from services.agents.nodes.draft import _format_section_context_block
from services.agents.state import FigureSlot, ProposalState, SectionContext
from services.citation_formatting import flag_unverified_freeform_citations
from services.agents.nodes import output as output_module
from services.agents.nodes.citation_verify import citation_verify_node
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


def test_draft_context_uses_registry_ids_and_only_section_sources(monkeypatch):
    prompts = []

    async def fake_search(**kwargs):
        return [
            {"id": "chunk-1", "source_id": "CR-001", "title": "Imaging paper", "text": "Researchers analyzed 20 scans in 2022."},
            {"id": "chunk-2", "source_id": "CR-002", "title": "Methods paper", "text": "Researchers surveyed 30 clinicians in 2021."},
        ]

    async def fake_llm(**kwargs):
        prompts.append(kwargs["prompt"])
        return "Researchers analyzed 20 scans in 2022 [CR-001]."

    async def skip_verification(section, excerpt_map, session_id=""):
        return section

    monkeypatch.setattr(draft_module, "semantic_search_session", fake_search)
    monkeypatch.setattr(draft_module, "call_llm", fake_llm)
    monkeypatch.setattr(draft_module, "verify_section", skip_verification)

    asyncio.run(
        draft_module.draft_node(
            {
                "topic": "medical imaging",
                "outline": {"sections": [{"name": "Imaging", "guidance": "imaging scans"}]},
                "citation_registry": [
                    {"id": "CR-001", "title": "Imaging paper", "evidence_level": "full_text"},
                    {"id": "CR-002", "title": "Methods paper", "evidence_level": "full_text"},
                ],
                "section_contexts": [{
                    "section_name": "Imaging",
                    "section_goal": "Discuss imaging scans.",
                    "assigned_sources": [{"id": "CR-001", "title": "Imaging paper", "evidence_level": "full_text"}],
                    "claims": [],
                    "narrative_prompt": "Use imaging evidence.",
                }],
            }
        )
    )

    assert "[CR-001 | Imaging paper]" in prompts[0]
    assert "Methods paper" not in prompts[0]


def test_draft_rebuilds_context_for_renamed_approved_section(monkeypatch):
    prompts = []
    hit = {
        "id": "chunk-1",
        "source_id": "CR-001",
        "title": "Updated methods paper",
        "text": "Survey methods evidence from the updated section source.",
        "distance": 0.1,
    }

    async def fake_search(**kwargs):
        return [hit]

    async def fake_llm(**kwargs):
        prompts.append(kwargs["prompt"])
        return "The survey methods are described [CR-001]."

    async def skip_verification(section, excerpt_map, session_id=""):
        return section

    monkeypatch.setattr(context_module, "semantic_search_session", fake_search)
    monkeypatch.setattr(draft_module, "semantic_search_session", fake_search)
    monkeypatch.setattr(draft_module, "call_llm", fake_llm)
    monkeypatch.setattr(draft_module, "verify_section", skip_verification)

    asyncio.run(
        draft_module.draft_node(
            {
                "topic": "research methods",
                "session_id": "edited-outline",
                "outline": {"sections": [{"name": "Updated Methods", "guidance": "Describe survey methods."}]},
                "citation_registry": [{
                    "id": "CR-001",
                    "title": "Updated methods paper",
                    "evidence_level": "full_text",
                }],
                "section_contexts": [{
                    "section_name": "Old Introduction",
                    "assigned_sources": [],
                    "claims": [],
                }],
            }
        )
    )

    assert "[CR-001 | Updated methods paper]" in prompts[0]
    assert "Survey methods evidence from the updated section source." in prompts[0]


def test_output_node_resolves_docx_citations_and_only_lists_used_sources(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        output_module,
        "save_report_to_supabase",
        lambda state: captured.update(saved_draft=state.get("draft_text")) or "report-1",
    )
    monkeypatch.setattr(
        output_module,
        "assemble_docx",
        lambda output, path: captured.update(output=output, path=path) or str(path),
    )

    asyncio.run(
        output_module.output_node(
            {
                "topic": "Test",
                "session_id": "session-1",
                "draft_text": "## Intro\nA claim [CR-001].",
                "generated_sections": [{"section_name": "Intro", "text": "A claim [CR-001]."}],
                "citation_registry": [
                    {"id": "CR-001", "title": "Used paper", "authors": "Doe, J.", "year": 2020},
                    {"id": "CR-002", "title": "Unused paper", "authors": "Roe, J.", "year": 2021},
                    {"id": "CR-003", "title": "Empty paper", "evidence_level": "none"},
                ],
            }
        )
    )

    output = captured["output"]
    assert "(Doe, 2020)" in captured["saved_draft"]
    assert "[CR-001]" not in captured["saved_draft"]
    assert "[CR-001]" not in output.sections[0].text
    assert "(Doe, 2020)" in output.sections[0].text
    assert len(output.references) == 1
    assert "Used paper" in output.references[0]
    assert "Unused paper" not in "\n".join(output.references)
    assert "Empty paper" not in "\n".join(output.references)


def test_citation_verifier_routes_retry_to_only_the_claim_section(monkeypatch):
    async def fake_llm(**kwargs):
        return '{"coverage_score": 0.5, "unverified_claims": [{"claim": "unsupported finding", "location": "Results"}]}'

    monkeypatch.setattr("services.agents.nodes.citation_verify.call_llm", fake_llm)
    result = asyncio.run(
        citation_verify_node(
            {
                "draft_text": "Draft",
                "citation_registry": [],
                "generated_sections": [
                    {"section_name": "Introduction", "text": "Context."},
                    {"section_name": "Results", "text": "An unsupported finding appears."},
                ],
            }
        )
    )

    assert result["citation_verification_result"]["retry_sections"] == ["Results"]
