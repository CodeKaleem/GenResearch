from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class ModelSpec:
    key: str
    model_id: str
    max_concurrent: int
    num_thread: int
    num_gpu: int = 0
    num_ctx: int = 4096


MODEL_REGISTRY: dict[str, ModelSpec] = {
    "heavy": ModelSpec(
        "heavy",
        settings.OLLAMA_HEAVY_MODEL,
        max_concurrent=settings.OLLAMA_HEAVY_MAX_CONCURRENT,
        num_thread=settings.OLLAMA_HEAVY_NUM_THREAD,
        num_gpu=settings.OLLAMA_HEAVY_NUM_GPU,
        num_ctx=8192,
    ),
    "mid": ModelSpec(
        "mid",
        settings.OLLAMA_MID_MODEL,
        max_concurrent=settings.OLLAMA_MID_MAX_CONCURRENT,
        num_thread=settings.OLLAMA_MID_NUM_THREAD,
        num_gpu=settings.OLLAMA_MID_NUM_GPU,
        num_ctx=6144,
    ),
    "light": ModelSpec(
        "light",
        settings.OLLAMA_LIGHT_MODEL,
        max_concurrent=settings.OLLAMA_LIGHT_MAX_CONCURRENT,
        num_thread=settings.OLLAMA_LIGHT_NUM_THREAD,
        num_gpu=settings.OLLAMA_LIGHT_NUM_GPU,
        num_ctx=4096,
    ),
}


ROLE_MODEL_CHAINS: dict[str, list[str]] = {
    "topic_analysis": ["mid", "light"],
    "summarization": ["light", "mid"],
    "citation_extraction": ["mid", "light"],
    "literature_review": ["heavy", "mid"],
    "proposal_composition": ["heavy", "mid"],
    "proposal_review": ["mid", "light"],
    "draft": ["heavy", "mid"],
    "citation_verification": ["heavy", "mid"],
    "sufficiency_evaluator": ["mid", "light"],
    "gap_report": ["mid", "light"],
    "outline_plan": ["mid", "light"],
    "source_quality_evaluator": ["mid", "light"],
    "user_doc_quality_eval": ["mid", "light"],
    "questionnaire": ["light", "mid"],
    "section_critic": ["light", "mid"],
    "final_qa": ["light", "mid"],
}


def get_chain_for_role(agent_role: str) -> list[ModelSpec]:
    keys = ROLE_MODEL_CHAINS.get(agent_role)
    if not keys:
        raise ValueError(
            f"Unknown agent role '{agent_role}'. "
            f"Valid roles: {sorted(ROLE_MODEL_CHAINS.keys())}"
        )
    return [MODEL_REGISTRY[key] for key in keys]


def list_registry() -> dict[str, dict]:
    return {
        key: {
            "model_id": spec.model_id,
            "max_concurrent": spec.max_concurrent,
            "num_thread": spec.num_thread,
        }
        for key, spec in MODEL_REGISTRY.items()
    }
