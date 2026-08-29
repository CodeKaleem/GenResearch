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

from services.llm_service import call_llm
from services.rag_service import semantic_search_session
from services.agents.prompts.draft import DRAFT_SYSTEM, build_draft_prompt

logger = logging.getLogger(__name__)


async def draft_node(state: dict) -> dict:
    """
    Stage 10: Generate the research paper draft.
    Uses the heavy model (lightning) with RAG context from ChromaDB.
    Every citation must reference an entry in the citation registry.
    """
    topic = state["topic"]
    outline = state.get("outline", {})
    registry = state.get("citation_registry", [])
    session_id = state.get("session_id", "unknown")
    citation_style = state.get("citation_style", "apa")

    # Build RAG context from session-scoped ChromaDB (A6/B1)
    rag_chunks = await semantic_search_session(
        session_id=session_id, query=topic, top_k=20
    )

    # Also search for each section's topic
    for section in outline.get("sections", [])[:5]:
        section_query = f"{topic} {section.get('name', '')}"
        section_chunks = await semantic_search_session(
            session_id=session_id, query=section_query, top_k=5
        )
        rag_chunks.extend(section_chunks)

    # Deduplicate by chunk id
    seen_ids = set()
    unique_chunks = []
    for c in rag_chunks:
        cid = c.get("id", "")
        if cid not in seen_ids:
            seen_ids.add(cid)
            unique_chunks.append(c)

    # Build RAG context text
    rag_context = "\n\n---\n\n".join(
        f"[Source: {c.get('title', 'Unknown')}]\n{c.get('text', '')}"
        for c in unique_chunks[:25]
    )

    prompt = build_draft_prompt(
        topic=topic, outline=outline, citation_registry=registry,
        rag_context=rag_context, citation_style=citation_style,
        approval_comment=state.get("approval_comment", "")
    )

    draft = await call_llm(
        prompt=prompt, agent_role="draft", system=DRAFT_SYSTEM,
        temperature=0.4, max_tokens=4096,
    )

    return {
        "draft_text": draft,
        "current_step": "draft",
        "status": "running",
        "steps_log": [
            f"✓ Draft generated ({len(draft)} chars, ~{len(draft.split())} words)"
        ],
    }
