"""Section-wise proposal composition and deterministic quality checks."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from models.schemas import GeneratedSection
from services.agents.verification_agent import verify_section
from services.llm_service import call_llm


SECTION_SPECS = [
    ("abstract", 200),
    ("introduction", 500),
    ("literature_review", 800),
    ("methodology", 500),
    ("expected_results", 300),
    ("timeline", 200),
]


async def compose_section(
    name: str,
    word_target: int,
    material: str,
    excerpt_map: dict[str, str],
    prior_sections: str = "",
    session_id: str = "",
) -> GeneratedSection:
    prompt = f"""Write only the {name} section of a research proposal.
Target length: approximately {word_target} words.
Use only the material below and cite factual claims with [E#] tags.
Avoid repeating material already covered in earlier sections.

EARLIER SECTIONS:
{prior_sections}

MATERIAL:
{material}
"""
    text = await call_llm(
        prompt,
        agent_role="composer",
        system="You are a careful academic proposal composer. Never invent evidence.",
        temperature=0.2,
        max_tokens=max(300, word_target * 2),
    )
    return await verify_section(GeneratedSection(section_name=name, text=text), excerpt_map, session_id)


async def compose_all_sections(
    topic: str,
    outline: dict,
    material: str,
    excerpt_map: dict[str, str],
    session_id: str = "",
) -> list[GeneratedSection]:
    """Compose sections sequentially so later sections can avoid repetition."""
    sections: list[GeneratedSection] = []
    specs = outline.get("sections") or [
        {"name": name, "word_target": target} for name, target in SECTION_SPECS
    ]
    prior = ""
    for spec in specs:
        name = spec.get("name", "section") if isinstance(spec, dict) else str(spec)
        target = int(spec.get("word_target", 400)) if isinstance(spec, dict) else 400
        section = await compose_section(name, target, f"Topic: {topic}\n{material}", excerpt_map, prior, session_id)
        sections.append(section)
        prior += f"\n{name}: {section.text}"
    return sections


def find_redundant_pairs(
    sections: list[GeneratedSection],
    threshold: float = 0.88,
) -> list[tuple[str, str, float]]:
    """Find near-duplicate sentences across sections without another LLM call."""
    sentences = [
        (section.section_name, sentence.strip())
        for section in sections
        for sentence in re.split(r"(?<=[.!?])\s+", section.text)
        if len(sentence.split()) >= 8
    ]
    pairs: list[tuple[str, str, float]] = []
    for index, (left_section, left) in enumerate(sentences):
        for right_section, right in sentences[index + 1:]:
            ratio = SequenceMatcher(None, left.lower(), right.lower()).ratio()
            if ratio >= threshold:
                pairs.append((f"{left_section}: {left}", f"{right_section}: {right}", ratio))
    return pairs


def lint_citations(text: str, registry: list[dict]) -> list[str]:
    """Return hard citation-reference errors for registry-bound [CR-###] tags."""
    known = {entry.get("id") for entry in registry}
    used = set(re.findall(r"\[CR-\d{3}\]", text))
    errors = [f"Missing registry entry for {tag}" for tag in sorted(used) if tag[1:-1] not in known]
    errors.extend(
        f"Registry entry {entry.get('id')} is not cited"
        for entry in registry
        if entry.get("id") and f"[{entry['id']}]" not in text
    )
    return errors