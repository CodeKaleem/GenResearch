# ============================================================
# Node: Draft Agent (Stage 10)
# Model: nemotron-3.5-lightning-30b-a3b (the ONLY heavy model)
# RAG-grounded, citation-registry bound.
#
# A6/B1: Uses session-scoped ChromaDB search — guarantees
#        that chunks from different topics never contaminate retrieval.
# ============================================================
from __future__ import annotations
import logging
import re

from services.llm_service import call_llm
from services.rag_service import semantic_search_session
from services.agents.prompts.draft import DRAFT_SYSTEM, build_draft_prompt
from services.citation_formatting import flag_unverified_freeform_citations
from services.agents.nodes.context_build import _select_relevant_sources

logger = logging.getLogger(__name__)


def _strip_duplicate_leading_heading(generated: str, section_name: str) -> str:
    """
    Deterministic backstop: across real runs, the draft agent has repeated
    the section title as the first line of its own body text in three
    different forms — bare ("Introduction"), as a markdown heading
    ("### Section 1: Introduction"), and bolded ("**Section 1:
    Introduction**") — despite an explicit prompt instruction against each
    form. Prompt wording alone hasn't reliably prevented this, so this
    strips whichever form shows up after the fact instead.
    """
    stripped = generated.lstrip()
    newline_idx = stripped.find("\n")
    first_line = stripped if newline_idx == -1 else stripped[:newline_idx]
    rest = "" if newline_idx == -1 else stripped[newline_idx + 1:]

    normalized = first_line.strip()
    normalized = re.sub(r"^#{1,6}\s*", "", normalized)
    normalized = re.sub(r"^\*+\s*", "", normalized)
    normalized = re.sub(r"\s*\*+\s*$", "", normalized)
    normalized = re.sub(r"^section\s*\d*\s*:\s*", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.rstrip(":").strip()

    if normalized.lower() == section_name.strip().lower():
        return rest.lstrip("\n").lstrip()
    return generated


def _format_section_context_block(section_context: dict) -> str:
    assigned_sources = section_context.get("assigned_sources", [])
    claims = section_context.get("claims", [])

    sources_block = (
        "\n".join(
            f"- [{source.get('id', 'UNKNOWN')}] {source.get('title', 'Untitled')}"
            for source in assigned_sources
        )
        if assigned_sources
        else "None. No real source is available for this section. Write conservatively, "
        "mark unsupported claims with [CITATION NEEDED], and do not invent sources or content."
    )
    claims_block = "\n".join(f"- {claim.get('text', '')}" for claim in claims) or "None."

    return (
        f"\n\nSECTION_CONTEXT:\n{section_context.get('narrative_prompt', '')}"
        f"\n\nSECTION_GOAL:\n{section_context.get('section_goal', '')}"
        "\n\nASSIGNED_SOURCES (cite only these by their exact registry ID; do not use freeform citations):"
        f"\n{sources_block}"
        f"\n\nCLAIMS TO WEAVE IN ONLY IF SUPPORTED BY THE ASSIGNED SOURCES:\n{claims_block}"
        "\n\nWrite only this section's body. Do not output a heading, section number, or repeat its title; "
        "the application inserts the heading."
    )


async def draft_node(state: dict) -> dict:
    """
    Stage 10: Generate the research paper draft.
    Uses the heavy model (lightning) with RAG context from ChromaDB.
    Every citation must reference an entry in the citation registry.

    The draft is assembled section-by-section using richer section context,
    and figure mounts are emitted as unrendered placeholders.
    """
    topic = state["topic"]
    outline = state.get("outline", {})
    registry = state.get("citation_registry", [])
    session_id = state.get("session_id", "unknown")
    citation_style = state.get("citation_style", "apa")
    section_contexts = state.get("section_contexts", [])

    rag_chunks = await semantic_search_session(
        session_id=session_id, query=topic, top_k=20
    )

    for section in outline.get("sections", [])[:5]:
        section_query = f"{topic} {section.get('name', '')}"
        section_chunks = await semantic_search_session(
            session_id=session_id, query=section_query, top_k=5
        )
        rag_chunks.extend(section_chunks)

    seen_ids = set()
    unique_chunks = []
    for c in rag_chunks:
        cid = c.get("id", "")
        if cid not in seen_ids:
            seen_ids.add(cid)
            unique_chunks.append(c)

    rag_context = "\n\n---\n\n".join(
        f"[Source: {c.get('title', 'Unknown')}]\n{c.get('text', '')}"
        for c in unique_chunks[:25]
    )

    if outline.get("sections"):
        sections = []
        draft_sections: list[str] = []

        for section in outline.get("sections", []):
            section_name = section.get("name", "Section")
            section_context = next(
                (item for item in section_contexts if item.get("section_name") == section_name),
                {
                    "section_name": section_name,
                    "section_goal": section.get("guidance", "Write the section with clear academic reasoning."),
                    "assigned_sources": _select_relevant_sources(
                        section_name, section.get("guidance", ""), registry
                    ),
                    "claims": [],
                    "figure_slots": [],
                    "narrative_prompt": f"Write the {section_name} section grounded in the research evidence.",
                },
            )

            prompt = build_draft_prompt(
                topic=topic,
                outline={"sections": [section]},
                citation_registry=registry,
                rag_context=rag_context,
                citation_style=citation_style,
                approval_comment=state.get("approval_comment", ""),
            )

            prompt += _format_section_context_block(section_context)

            generated = await call_llm(
                prompt=prompt,
                agent_role="draft",
                system=DRAFT_SYSTEM,
                temperature=0.4,
                max_tokens=3000,
            )

            generated = flag_unverified_freeform_citations(generated.strip())
            generated = _strip_duplicate_leading_heading(generated, section_name)

            section_payload = {
                "section_name": section_name,
                "text": generated,
                "claims": section_context.get("claims", []),
            }
            sections.append(section_payload)
            draft_sections.append(f"## {section_name}\n{generated}")

        draft = "\n\n".join(draft_sections)
        return {
            "draft_text": draft,
            "generated_sections": sections,
            "current_step": "draft",
            "status": "running",
            "steps_log": [
                f"✓ Composed {len(sections)} section-level drafts"
            ],
        }

    prompt = build_draft_prompt(
        topic=topic, outline=outline, citation_registry=registry,
        rag_context=rag_context, citation_style=citation_style,
        approval_comment=state.get("approval_comment", "")
    )

    draft = await call_llm(
        prompt=prompt, agent_role="draft", system=DRAFT_SYSTEM,
        temperature=0.4, max_tokens=4096,
    )
    draft = flag_unverified_freeform_citations(draft)

    return {
        "draft_text": draft,
        "current_step": "draft",
        "status": "running",
        "steps_log": [
            f"✓ Draft generated ({len(draft)} chars, ~{len(draft.split())} words)"
        ],
    }
