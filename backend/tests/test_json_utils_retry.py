"""Regression tests for shared LLM JSON parsing and judge retry decisions."""
import asyncio

from services.agents.json_utils import coerce_score, parse_llm_json
from services.agents.nodes.citation_verify import citation_verify_node
from services.agents.nodes.final_qa import final_qa_node
from services.agents.nodes.section_critic import section_critic_node
from services.agents.pipeline_graph import route_final_qa
from services.agents.prompts.final_qa import FINAL_QA_SYSTEM
from services.agents.retry import MAX_RETRIES, should_retry
from services.llm_models import ROLE_MODEL_CHAINS
from services.report_store import build_completion_guide_text


def test_parser_handles_fences_nested_braces_and_trailing_text():
    parsed = parse_llm_json(
        '```json\n{"summary":"brace } inside string", "nested":{"score":8}}\n``` done'
    )

    assert parsed == {"summary": "brace } inside string", "nested": {"score": 8}}


def test_parser_returns_none_for_invalid_json():
    assert parse_llm_json("```json\nnot json\n```") is None


def test_score_coercion_accepts_strings_and_percent_coverage():
    assert coerce_score("7.5") == 7.5
    assert coerce_score("85", percentage=True) == 0.85
    assert coerce_score("invalid") is None


def test_retry_decision_uses_explicit_completed_attempts():
    state = {"retry_counts": {"judge": 100}}

    assert should_retry(state, "judge", False, "issue", attempts_done=1) == "retry"
    assert should_retry(state, "judge", False, "issue", attempts_done=MAX_RETRIES) == "retry"
    assert should_retry(state, "judge", False, "issue", attempts_done=MAX_RETRIES + 1) == "flag"


def test_final_qa_flags_after_three_failed_judgments(monkeypatch):
    calls = 0

    async def fake_call_llm(**kwargs):
        nonlocal calls
        calls += 1
        return '{"overall_score":"3.5","issues":["insufficient evidence"]}'

    monkeypatch.setattr("services.agents.nodes.final_qa.call_llm", fake_call_llm)
    state = {"draft_text": "Draft text", "retry_counts": {}}
    final_update = None

    for _ in range(3):
        final_update = asyncio.run(final_qa_node(state))
        state.update(final_update)

    assert calls == 3
    assert final_update is not None
    assert final_update["flagged_items"]
    assert route_final_qa(state) == "output"


def test_unparseable_final_qa_retries_once_then_passes_with_flag(monkeypatch):
    async def fake_call_llm(**kwargs):
        return "not valid JSON"

    monkeypatch.setattr("services.agents.nodes.final_qa.call_llm", fake_call_llm)
    state = {"draft_text": "Draft text", "retry_counts": {}}

    first = asyncio.run(final_qa_node(state))
    state.update(first)
    assert first["final_qa_result"]["unknown"] is True
    assert route_final_qa(state) == "final_qa"

    second = asyncio.run(final_qa_node(state))

    assert second["final_qa_result"]["passed"] is True
    assert second["flagged_items"]


def test_citation_percentage_and_critic_string_scores_are_normalized(monkeypatch):
    async def fake_citation_llm(**kwargs):
        return '{"coverage_score":"85","unverified_claims":[]}'

    async def fake_critic_llm(**kwargs):
        return '{"overall_score":"8.5","summary":"clear","sections":{}}'

    monkeypatch.setattr("services.agents.nodes.citation_verify.call_llm", fake_citation_llm)
    citation_result = asyncio.run(
        citation_verify_node({"draft_text": "Draft", "citation_registry": []})
    )
    monkeypatch.setattr("services.agents.nodes.section_critic.call_llm", fake_critic_llm)
    critic_result = asyncio.run(
        section_critic_node({"draft_text": "Draft", "outline": {}})
    )

    assert citation_result["citation_verification_result"]["coverage_score"] == 0.85
    assert citation_result["citation_verification_result"]["passed"] is True
    assert critic_result["section_critic_result"]["overall_score"] == 8.5
    assert critic_result["section_critic_result"]["passed"] is True


def test_completion_guide_displays_unknown_citation_score_without_crashing():
    guide = build_completion_guide_text({
        "citation_verification_result": {"coverage_score": None, "unknown": True},
    })

    assert "Citation Grounding:** unknown coverage" in guide


def test_final_qa_does_not_judge_references_before_they_exist():
    assert "Reference Completeness" not in FINAL_QA_SYSTEM
    assert ROLE_MODEL_CHAINS["citation_verification"] != ROLE_MODEL_CHAINS["draft"]
    assert ROLE_MODEL_CHAINS["citation_verification"][0] == "mid"