"""Regression coverage for joins and human-resume paths in the real graph."""
import asyncio

import pytest
from langgraph.checkpoint.memory import MemorySaver

from services.agents import pipeline_graph as graph_module
from services.agents.nodes.sufficiency_eval import sufficiency_eval_node


def _node_stub(name, events):
    async def node(state: dict) -> dict:
        events.append((name, state.get("citation_registry", [])))
        if name == "sufficiency_eval":
            assessment = state.get("questionnaire_answers", {}).get(
                "test_assessment", "sufficient"
            )
            attempts = state.get("retry_counts", {}).get("sufficiency_eval", 0)
            return {
                "sufficiency_report": {"overall_assessment": assessment},
                "retry_counts": {"sufficiency_eval": attempts + 1},
                "steps_log": [name],
            }
        if name == "ingestion":
            return {
                "citation_registry": [{"id": "CR-001", "title": "Evidence"}],
                "steps_log": [name],
            }
        if name == "citation_verify":
            return {"citation_verification_result": {"passed": True}, "steps_log": [name]}
        if name == "section_critic":
            return {"section_critic_result": {"passed": True}, "steps_log": [name]}
        if name == "final_qa":
            return {"final_qa_result": {"passed": True}, "steps_log": [name]}
        return {"steps_log": [name]}

    return node


@pytest.fixture
def graph_with_events(monkeypatch):
    events = []
    node_names = [
        "topic_input_node", "questionnaire_node", "user_doc_quality_eval_node",
        "sufficiency_eval_node", "scrape_permission_node", "gap_report_node",
        "outline_plan_node", "context_build_node", "source_gathering_node",
        "source_quality_eval_node", "ingestion_node", "merge_ab_node",
        "user_approval_node", "draft_node", "citation_verify_node",
        "section_critic_node", "merge_cd_node", "final_qa_node", "output_node",
    ]
    graph_names = {
        "topic_input_node": "topic_input", "questionnaire_node": "questionnaire",
        "user_doc_quality_eval_node": "user_doc_quality_eval",
        "sufficiency_eval_node": "sufficiency_eval", "scrape_permission_node": "scrape_permission",
        "gap_report_node": "gap_report", "outline_plan_node": "outline_plan",
        "context_build_node": "context_build", "source_gathering_node": "source_gathering",
        "source_quality_eval_node": "source_quality_eval", "ingestion_node": "ingestion",
        "merge_ab_node": "merge_ab", "user_approval_node": "user_approval",
        "draft_node": "draft", "citation_verify_node": "citation_verify",
        "section_critic_node": "section_critic", "merge_cd_node": "merge_cd",
        "final_qa_node": "final_qa", "output_node": "output",
    }
    for attribute in node_names:
        monkeypatch.setattr(
            graph_module,
            attribute,
            _node_stub(graph_names[attribute], events),
        )

    graph = graph_module.build_pipeline_graph().compile(
        checkpointer=MemorySaver(),
        interrupt_before=["user_doc_quality_eval", "scrape_permission", "user_approval"],
    )
    return graph, events


@pytest.mark.parametrize("scenario", ["sufficient", "granted", "denied"])
def test_ingestion_and_joins_complete_before_draft(graph_with_events, scenario):
    graph, events = graph_with_events
    config = {"configurable": {"thread_id": f"pipeline-{scenario}"}}
    initial = {
        "topic": "test topic",
        "session_id": scenario,
        "questionnaire_answers": {
            "test_assessment": "sufficient" if scenario == "sufficient" else "needs_more"
        },
        "steps_log": [],
    }

    async def stream(value):
        async for _ in graph.astream(value, config=config, stream_mode="updates"):
            pass

    asyncio.run(stream(initial))
    assert graph.get_state(config).next == ("user_doc_quality_eval",)
    graph.update_state(
        config,
        {"questionnaire_answers": initial["questionnaire_answers"]},
        as_node="questionnaire",
    )
    asyncio.run(stream(None))

    if scenario != "sufficient":
        assert graph.get_state(config).next == ("scrape_permission",)
        graph.update_state(
            config,
            {"scrape_permission_granted": scenario == "granted"},
            as_node="sufficiency_eval",
        )
        asyncio.run(stream(None))

    state = graph.get_state(config)
    assert state.next == ("user_approval",)
    graph.update_state(config, {"status": "approved"}, as_node="context_build")
    asyncio.run(stream(None))

    names = [name for name, _ in events]
    assert names.count("ingestion") == 1
    assert names.count("merge_ab") == 1
    assert names.count("merge_cd") == 1
    assert names.index("ingestion") < names.index("context_build")
    assert names.index("context_build") < names.index("draft")
    assert names.index("citation_verify") < names.index("merge_cd")
    assert names.index("section_critic") < names.index("merge_cd")
    assert next(registry for name, registry in events if name == "context_build")
    assert next(registry for name, registry in events if name == "draft")


def test_deterministic_source_count_override_skips_sufficiency_retry(monkeypatch):
    async def fake_call_llm(**kwargs):
        return '{"overall_assessment":"sufficient","sections":{},"summary":"looks good"}'

    monkeypatch.setattr(
        "services.agents.nodes.sufficiency_eval.call_llm", fake_call_llm
    )
    result = asyncio.run(
        sufficiency_eval_node(
            {
                "topic": "test",
                "user_provided_sources": [{"title": "one"}, {"title": "two"}],
                "retry_counts": {"sufficiency_eval": 0},
            }
        )
    )

    assert result["sufficiency_report"]["overall_assessment"] == "needs_more"
    assert result["sufficiency_report"]["source_count_override"] is True
    assert "sufficiency_eval" not in result.get("retry_feedback", {})
    assert graph_module.route_sufficiency(result) == "scrape_permission"