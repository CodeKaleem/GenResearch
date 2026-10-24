"""Regression tests for batched source-quality evaluation prompts."""
import asyncio
import json

from services.agents.nodes import source_quality_eval
from services.llm_models import ROLE_MODEL_CHAINS


def test_batch_prompt_encodes_source_fields_as_valid_json(monkeypatch):
    prompts = []

    async def fake_call_llm(**kwargs):
        prompts.append(kwargs["prompt"])
        return '{"0":{"passed":true,"credibility":"high","relevance_score":8}}'

    monkeypatch.setattr(source_quality_eval, "call_llm", fake_call_llm)
    sources = [{
        "title": "Farmer's " + '"resilient"' + " crop study",
        "year": 2024,
        "abstract_snippet": "A useful study\\with quoted text.",
        "citation_count": 12,
    }]

    result = asyncio.run(
        source_quality_eval._evaluate_batch(sources, [3], "crop resilience", "drought")
    )

    serialized_sources = prompts[0].split("Sources to evaluate:\n", 1)[1].split(
        "\n\nEvaluate each source.", 1
    )[0]
    assert json.loads(serialized_sources) == {
        "0": {
            "title": sources[0]["title"],
            "year": 2024,
            "abstract": sources[0]["abstract_snippet"],
            "citations": 12,
        }
    }
    assert result[3]["passed"] is True


def test_prefilter_rejects_sources_missing_abstract_or_year():
    source = {
        "title": "Crop resilience study",
        "abstract_snippet": "A detailed study on crop resilience and drought response.",
    }

    assert source_quality_eval._pre_filter_source(source, "crop resilience") == (
        False,
        "Missing or invalid publication year",
    )
    source["year"] = 2024
    source["abstract_snippet"] = ""
    assert source_quality_eval._pre_filter_source(source, "crop resilience") == (
        False,
        "No usable abstract",
    )


def test_source_quality_evaluation_prefers_light_model():
    assert ROLE_MODEL_CHAINS["source_quality_evaluator"] == ["light", "mid"]