"""Regression coverage for the deterministic sufficiency source-count floor."""
import asyncio
import json

from services.agents.nodes import sufficiency_eval as sufficiency_module


def _run_with_fake_llm(monkeypatch, fake_response: dict, user_sources: list[dict]):
    async def fake_call_llm(**kwargs):
        return json.dumps(fake_response)

    monkeypatch.setattr(sufficiency_module, "call_llm", fake_call_llm)
    state = {
        "topic": "AI in medical science",
        "questionnaire_answers": {"q1": "detailed answer"},
        "user_provided_sources": user_sources,
    }
    return asyncio.run(sufficiency_module.sufficiency_eval_node(state))


def test_sufficient_verdict_is_overridden_below_minimum(monkeypatch):
    result = _run_with_fake_llm(
        monkeypatch,
        {"overall_assessment": "sufficient", "summary": "Looks fine."},
        [{"title": "One source", "tag": "uploaded"}],
    )
    report = result["sufficiency_report"]
    assert report["overall_assessment"] == "needs_more"
    assert "Overridden" in report["summary"]


def test_sufficient_verdict_is_trusted_at_minimum(monkeypatch):
    result = _run_with_fake_llm(
        monkeypatch,
        {"overall_assessment": "sufficient", "summary": "Well covered."},
        [{"title": f"Paper {letter}", "tag": "uploaded"} for letter in "ABC"],
    )
    report = result["sufficiency_report"]
    assert report["overall_assessment"] == "sufficient"
    assert report["summary"] == "Well covered."


def test_needs_more_verdict_is_never_relaxed(monkeypatch):
    result = _run_with_fake_llm(
        monkeypatch,
        {"overall_assessment": "needs_more", "summary": "Thin coverage."},
        [{"title": f"Paper {index}", "tag": "uploaded"} for index in range(4)],
    )
    report = result["sufficiency_report"]
    assert report["overall_assessment"] == "needs_more"
    assert report["summary"] == "Thin coverage."
