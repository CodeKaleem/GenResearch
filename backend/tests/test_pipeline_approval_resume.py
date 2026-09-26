"""Regression coverage for the pipeline approval checkpoint resume behavior."""
import asyncio
import inspect

import pytest
from langgraph.checkpoint.memory import MemorySaver

import routers.pipeline as pipeline_router
from services.agents import pipeline_graph as graph_module
from services.agents.nodes.user_approval import user_approval_node


def _stub(name):
    async def node(state: dict) -> dict:
        return {"steps_log": state.get("steps_log", []) + [name]}

    return node


@pytest.fixture
def stubbed_graph(monkeypatch):
    """Build the real graph topology with inexpensive stub nodes."""
    for name in [
        "topic_input_node",
        "questionnaire_node",
        "user_doc_quality_eval_node",
        "sufficiency_eval_node",
        "scrape_permission_node",
        "gap_report_node",
        "outline_plan_node",
        "context_build_node",
        "source_gathering_node",
        "source_quality_eval_node",
        "ingestion_node",
        "merge_ab_node",
        "draft_node",
        "citation_verify_node",
        "section_critic_node",
        "merge_cd_node",
        "final_qa_node",
        "output_node",
    ]:
        monkeypatch.setattr(graph_module, name, _stub(name))
    monkeypatch.setattr(graph_module, "user_approval_node", user_approval_node)

    workflow = graph_module.build_pipeline_graph()
    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=[
            "user_doc_quality_eval",
            "scrape_permission",
            "user_approval",
        ],
    )


def _drive_to_approval_interrupt(graph, thread_id):
    """Advance through the questionnaire pause and stop at user approval."""
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "topic": "test",
        "outline": {"sections": [{"name": "Introduction"}]},
        "citation_registry": [],
        "steps_log": [],
        "sufficiency_report": {"overall_assessment": "sufficient"},
    }

    async def stream(input_state):
        async for _ in graph.astream(input_state, config=config, stream_mode="updates"):
            pass

    asyncio.run(stream(initial_state))
    assert graph.get_state(config).next == ("user_doc_quality_eval",)

    graph.update_state(config, {"questionnaire_answers": {}}, as_node="questionnaire")
    asyncio.run(stream(None))

    assert graph.get_state(config).next == ("user_approval",)
    return config


def test_approve_endpoint_uses_direct_predecessor_as_node():
    source = inspect.getsource(pipeline_router.approve_pipeline)
    assert 'as_node="context_build"' in source
    assert 'as_node="merge_ab"' not in source


def test_resuming_two_hops_back_loops_instead_of_advancing(stubbed_graph):
    config = _drive_to_approval_interrupt(stubbed_graph, "buggy-thread")
    stubbed_graph.update_state(config, {"status": "approved"}, as_node="merge_ab")

    async def resume():
        async for _ in stubbed_graph.astream(None, config=config, stream_mode="updates"):
            pass

    asyncio.run(resume())
    assert stubbed_graph.get_state(config).next == ("user_approval",)


def test_resuming_from_direct_predecessor_advances_past_approval(stubbed_graph):
    config = _drive_to_approval_interrupt(stubbed_graph, "fixed-thread")
    stubbed_graph.update_state(
        config, {"status": "approved"}, as_node="context_build"
    )

    async def resume():
        async for _ in stubbed_graph.astream(None, config=config, stream_mode="updates"):
            pass

    asyncio.run(resume())

    final_state = stubbed_graph.get_state(config)
    assert "user_approval" not in final_state.next
    assert "draft_node" in final_state.values.get("steps_log", [])
