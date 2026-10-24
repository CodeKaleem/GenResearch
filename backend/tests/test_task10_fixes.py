"""Regression coverage for Task 10 reporting and data-contract fixes."""
import asyncio
import hashlib
import logging

from docx import Document

from routers import agent_tasks, pipeline
from services import source_gathering, tracking
from services.agents.assembly_agent import assemble_docx, human_input_checklist
from services.agents.literature_review_agent import run_literature_review
from services.agents.nodes.scrape_permission import scrape_permission_node
from services.agents.pipeline_graph import route_scrape_permission
from services.agents.proposal_graph import review_proposal
from models.schemas import GeneratedSection, ProposalOutput


def test_completion_guide_handles_malformed_sections_and_scores():
    from services.report_store import build_completion_guide_text

    guide = build_completion_guide_text({
        "topic": "test",
        "sufficiency_report": {
            "overall_assessment": "adequate",
            "sections": {"Introduction": "weak", "Methods": None},
        },
        "citation_verification_result": {"coverage_score": "not-a-score"},
        "section_critic_result": {"overall_score": "unknown"},
        "final_qa_result": {"overall_score": None},
    })

    assert "Introduction" in guide
    assert "Citation Grounding:** unknown coverage" in guide
    assert "Writing Quality:** unknown/10" in guide
    assert "Overall Pipeline QA:** unknown/10" in guide


def test_quality_scores_are_scaled_before_database_storage():
    assert pipeline._scale_qa_score(7.8) == 78
    assert pipeline._scale_qa_score(None) is None
    assert pipeline._scale_qa_score("bad") is None


def test_agent_task_types_map_to_database_enum(monkeypatch):
    stored = []
    monkeypatch.setattr(agent_tasks.tracking, "create_task", lambda *args, **kwargs: "task-1")
    monkeypatch.setattr(agent_tasks.tracking, "complete_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_tasks.tracking, "save_task_result", lambda **kwargs: stored.append(kwargs))
    monkeypatch.setattr(agent_tasks.tracking, "log_agent_event", lambda *args, **kwargs: None)

    async def run_agent():
        return {"summary": "text"}

    asyncio.run(
        agent_tasks._run_tracked_agent(
            user_id="user-1",
            title="summary",
            agent_type="summarization",
            paper_ids=["paper-1"],
            run=run_agent,
        )
    )

    assert stored[0]["type_"] == "summary"


def test_tracking_insert_logs_failure_at_warning(monkeypatch, caplog):
    def fail_client():
        raise RuntimeError("database offline")

    monkeypatch.setattr(tracking, "get_supabase", fail_client)
    with caplog.at_level(logging.WARNING):
        tracking._insert("task_results", {"type": "summary"})

    assert "tracking_insert_failed" in caplog.text


def test_scrape_denial_flag_is_emitted_by_node_not_router():
    state = {"scrape_permission_granted": False, "flagged_items": []}
    destinations = route_scrape_permission(state)
    node_result = asyncio.run(scrape_permission_node(state))

    assert destinations == ["outline_plan", "ingestion"]
    assert state["flagged_items"] == []
    assert node_result["flagged_items"][0]["node"] == "scrape_permission"


def test_docx_checklist_and_markdown_rendering_are_case_insensitive_and_clean(tmp_path):
    output = ProposalOutput(
        topic="Test Proposal",
        sections=[GeneratedSection(
            section_name="Methodology",
            text="### Data Collection\n\n**interviews** with participants.",
        )],
    )

    checklist = human_input_checklist(output)
    assert any("interview" in item.lower() for item in checklist)
    path = tmp_path / "proposal.docx"
    assemble_docx(output, path)
    paragraphs = Document(path).paragraphs

    assert any(p.text == "Data Collection" and p.style.name == "Heading 3" for p in paragraphs)
    assert all("**" not in p.text and not p.text.startswith("###") for p in paragraphs)


def test_crossref_falls_back_for_year_cleans_jats_and_keeps_long_abstract():
    abstract = "<jats:p>" + ("A detailed result. " * 100) + "</jats:p>"

    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def json(self):
            return {"message": {"items": [{
                "title": ["Crossref result"],
                "issued": {"date-parts": [[2022, 4, 1]]},
                "abstract": abstract,
            }]}}

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    result = asyncio.run(source_gathering.search_crossref("query", session=Session()))
    source = result["results"][0]

    assert source["year"] == 2022
    assert "<jats:p>" not in source["abstract_snippet"]
    assert len(source["abstract_snippet"]) > 300


def test_source_gathering_handles_none_titles_without_crashing(monkeypatch):
    async def one_source(query, limit=5, session=None):
        return {"status": "success", "results": [{"title": None, "abstract_snippet": "evidence"}]}

    async def no_sources(query, limit=5, session=None):
        return {"status": "success", "results": []}

    monkeypatch.setattr(source_gathering, "search_semantic_scholar", one_source)
    monkeypatch.setattr(source_gathering, "search_arxiv", no_sources)
    monkeypatch.setattr(source_gathering, "search_crossref", no_sources)
    monkeypatch.setattr(source_gathering, "search_openalex", no_sources)

    found, unfilled, errors = asyncio.run(
        source_gathering.gather_sources_for_gaps(
            [{"topic": "test", "search_query": "test"}], sources_per_gap=1
        )
    )

    assert not found
    assert len(unfilled) == 1
    assert not errors


def test_source_gathering_uses_and_deduplicates_api_results(monkeypatch):
    async def semantic_scholar(query, limit=5, session=None):
        return {"status": "success", "results": [{"title": "Shared paper"}]}

    async def crossref(query, limit=5, session=None):
        return {"status": "success", "results": [
            {"title": "Shared paper"},
            {"title": "Crossref paper"},
        ]}

    async def openalex(query, limit=5, session=None):
        return {"status": "success", "results": [{"title": "OpenAlex paper"}]}

    async def arxiv(query, limit=5, session=None):
        return {"status": "success", "results": [{"title": "arXiv paper"}]}

    monkeypatch.setattr(source_gathering, "search_semantic_scholar", semantic_scholar)
    monkeypatch.setattr(source_gathering, "search_crossref", crossref)
    monkeypatch.setattr(source_gathering, "search_openalex", openalex)
    monkeypatch.setattr(source_gathering, "search_arxiv", arxiv)

    found, unfilled, errors = asyncio.run(
        source_gathering.gather_sources_for_gaps(
            [{"topic": "Crop resilience", "search_query": "Crop resilience"}],
            sources_per_gap=3,
        )
    )

    assert [source["title"] for source in found] == [
        "Shared paper",
        "Crossref paper",
        "OpenAlex paper",
    ]
    assert len({source["title"] for source in found}) == len(found)
    assert not unfilled
    assert not errors


def test_literature_review_keeps_top_chunks_per_paper(monkeypatch):
    seen_prompt = []
    seen_queries = []
    distances = {"paper-1": 0.0, "paper-2": 0.3, "paper-3": 0.6}

    async def fake_search(user_id, query, top_k, paper_id):
        seen_queries.append(query)
        return [{
            "id": f"{paper_id}-{index}",
            "paper_id": paper_id,
            "title": f"Paper {paper_id}",
            "metadata": {"authors": "Smith, J.", "year": 2024},
                "text": f"Evidence from {paper_id}, {query}, chunk {index}.",
            "distance": distances[paper_id] + index / 1000,
        } for index in range(10)]

    async def fake_llm(*args, **kwargs):
        seen_prompt.append(kwargs["prompt"])
        if "Audit the draft" in kwargs["prompt"]:
            source_id = "CR-" + hashlib.sha256(b"paper-1").hexdigest()[:12].upper()
            return (
                '{"issues": [], "corrected_review": "## Introduction\\n'
                f'Evidence from this paper demonstrates significant clinical benefit [{source_id}]. '
                'Another finding remains entirely unsupported by any literature cited."}'
            )
        if "Extract bibliographic metadata" in kwargs["prompt"]:
            return '{"sources": []}'
        return "Draft review"

    async def fake_records(user_id, paper_ids):
        return {
            paper_id: {
                "id": paper_id,
                "title": f"Paper {paper_id}",
                "authors": "Smith, J.",
                "year": 2024,
                "file_name": f"{paper_id}.pdf",
            }
            for paper_id in paper_ids
        }

    monkeypatch.setattr("services.agents.literature_review_agent.semantic_search", fake_search)
    monkeypatch.setattr("services.agents.literature_review_agent.call_llm", fake_llm)
    monkeypatch.setattr("services.agents.literature_review_agent._load_paper_records", fake_records)
    result = asyncio.run(
        run_literature_review("user-1", ["paper-1", "paper-2", "paper-3"])
    )

    review_prompt = next(prompt for prompt in seen_prompt if "SOURCE KEY" in prompt)
    for paper_id in ("paper-1", "paper-2", "paper-3"):
        assert f"Paper {paper_id}" in review_prompt
    assert len(seen_queries) == 21
    assert any("methodology" in query for query in seen_queries)
    assert any("limitations" in query for query in seen_queries)
    assert any("adoption determinants" in query for query in seen_queries)
    assert any("journal DOI" in query for query in seen_queries)
    assert result["papers_analyzed"] == 3
    assert result["chunks_used"] == 12
    assert "(Smith, 2024)" in result["review"]
    assert "## References" in result["review"]
    assert result["verification"]["completed"] is True
    # [CITATION NEEDED] must NOT appear in the final text — uncited claims go to review_list
    assert "[CITATION NEEDED]" not in result["review"]
    assert result["citation_quality"]["uncited_sentences"] == 1
    assert result["citation_quality"]["coverage"] < 1
    assert result["citation_quality"]["sources_cited"] == 1
    assert len(result["citation_quality"]["sources_uncited"]) == 2


def test_literature_review_citation_ids_are_stable_for_each_paper():
    from services.agents.literature_review_agent import _paper_metadata

    chunk = {"title": "A verifiable title", "metadata": {}}
    first = _paper_metadata([chunk], "paper-id-a")
    second = _paper_metadata([chunk], "paper-id-b")
    assert first["id"] == _paper_metadata([chunk], "paper-id-a")["id"]
    assert first["id"] != second["id"]


def test_proposal_review_keeps_original_when_rewrite_is_too_short(monkeypatch):
    original = "A complete original proposal. " * 50

    async def fake_llm(**kwargs):
        return "A much shorter rewrite."

    monkeypatch.setattr("services.agents.proposal_graph.call_llm", fake_llm)
    result = asyncio.run(review_proposal({"proposal": original}))

    assert result["proposal"] == original