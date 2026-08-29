# ============================================================
# Node: Questionnaire Agent (Stage 2)
# Generates dynamic, topic-specific questions.
# Model: nemotron-3-nano (cheap, fast — task is generation, not deep reasoning)
# ============================================================
from __future__ import annotations

import json
import logging

from services.llm_service import call_llm
from services.agents.prompts.questionnaire import (
    QUESTIONNAIRE_SYSTEM,
    build_questionnaire_prompt,
)

logger = logging.getLogger(__name__)


async def questionnaire_node(state: dict) -> dict:
    """
    Stage 2: Generate a dynamic questionnaire for the user's research topic.
    Output is structured JSON so the frontend can render it without hand-coding.
    """
    topic = state["topic"]

    prompt = build_questionnaire_prompt(topic)

    raw = await call_llm(
        prompt=prompt,
        agent_role="questionnaire",
        system=QUESTIONNAIRE_SYSTEM,
        temperature=0.4,
        max_tokens=1500,
    )

    # Parse JSON — handle models that wrap in markdown code blocks
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` wrapper
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    try:
        questions_data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("questionnaire_json_parse_failed", extra={"raw": raw[:500]})
        # Fallback: wrap raw text as a single text question
        questions_data = {
            "questions": [
                {
                    "id": "q1",
                    "question": "Please describe your existing research material and what you'd like to focus on.",
                    "type": "text",
                    "required": True,
                    "hint": "Share whatever you already have — we'll tell you if we need anything else.",
                }
            ]
        }

    return {
        "questionnaire_questions": questions_data.get("questions", []),
        "status": "awaiting_input",
        "current_step": "questionnaire",
        "steps_log": [
            f"✓ Generated {len(questions_data.get('questions', []))} topic-specific questions"
        ],
    }
