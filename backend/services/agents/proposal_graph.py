# ============================================================
# GenResearch — Proposal Draft Agent (LangGraph Orchestrator)
# Multi-agent workflow: Topic Analysis → Literature Retrieval →
# Summarization → Literature Review → Citations → Proposal Composition
# ============================================================
from __future__ import annotations

import json as json_lib
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

from services.llm_service import call_llm
from services.rag_service import semantic_search
from services.agents.summarization_agent import run_summarization
from services.agents.literature_review_agent import run_literature_review
from services.agents.citation_agent import run_citation_extraction


# ── State Schema ──────────────────────────────────────────────
class ProposalState(TypedDict):
    # Inputs
    user_id: str
    paper_ids: list[str]
    topic: str
    # Intermediate results from sub-agents
    topic_analysis: str
    relevant_chunks: list[dict]
    summaries: list[dict]
    literature_review: str
    citations: str
    # Final output
    proposal: str
    status: str
    current_step: str
    steps_log: list[str]


# ── Node Functions ────────────────────────────────────────────

async def analyze_topic(state: ProposalState) -> dict:
    """
    Step 1: Analyze the user's research topic.
    Define scope, boundaries, key research questions, and objectives.
    """
    topic = state["topic"]

    # Also pull relevant content from uploaded papers to ground the analysis
    chunks = await semantic_search(
        user_id=state["user_id"],
        query=topic,
        top_k=10,
    )

    context = ""
    if chunks:
        context = "\n\n".join(
            f"[From: {c.get('title', 'Unknown')}]\n{c['text']}"
            for c in chunks[:5]
        )
        context = f"\n\nRelevant background from uploaded papers:\n{context}"

    prompt = f"""Analyze the following research topic and produce a structured topic analysis.

Research Topic: "{topic}"
{context}

Produce the following:
1. **Refined Research Title**: A clear, academic title for this research
2. **Research Problem Statement**: What problem does this research address? (2-3 sentences)
3. **Research Objectives**: 3-5 specific, measurable objectives
4. **Key Research Questions**: 3-4 questions this research aims to answer
5. **Scope & Boundaries**: What is included and excluded
6. **Expected Contribution**: How this research will contribute to the field

Be specific, academic, and grounded in the available literature."""

    analysis = await call_llm(
        prompt=prompt,
        system="You are an expert research methodology advisor specializing in defining research scope and objectives.",
        temperature=0.3,
        max_tokens=1500,
    )

    return {
        "topic_analysis": analysis,
        "relevant_chunks": chunks,
        "current_step": "topic_analysis",
        "steps_log": state.get("steps_log", []) + ["✓ Topic analysis completed"],
    }


async def retrieve_literature(state: ProposalState) -> dict:
    """
    Step 2: Deep retrieval of relevant content from all selected papers.
    Uses multiple queries to find diverse relevant chunks.
    """
    topic = state["topic"]
    paper_ids = state["paper_ids"]

    # Multiple search queries for comprehensive coverage
    search_queries = [
        topic,
        f"methodology approach {topic}",
        f"results findings {topic}",
        f"challenges limitations {topic}",
        f"future work recommendations {topic}",
    ]

    all_chunks: list[dict] = []
    seen_ids: set[str] = set()

    for query in search_queries:
        for paper_id in paper_ids:
            chunks = await semantic_search(
                user_id=state["user_id"],
                query=query,
                top_k=5,
                paper_id=paper_id,
            )
            for c in chunks:
                if c["id"] not in seen_ids:
                    seen_ids.add(c["id"])
                    all_chunks.append(c)

    # Sort by relevance
    all_chunks.sort(key=lambda c: c.get("distance", 1.0))

    return {
        "relevant_chunks": all_chunks[:30],  # Keep top 30
        "current_step": "literature_retrieval",
        "steps_log": state.get("steps_log", []) + [
            f"✓ Retrieved {len(all_chunks)} relevant excerpts from {len(paper_ids)} papers"
        ],
    }


async def generate_summaries(state: ProposalState) -> dict:
    """
    Step 3: Run the summarization sub-agent on selected papers.
    """
    result = await run_summarization(
        user_id=state["user_id"],
        paper_ids=state["paper_ids"],
    )

    return {
        "summaries": result["summaries"],
        "current_step": "summarization",
        "steps_log": state.get("steps_log", []) + [
            f"✓ Generated summaries for {len(result['summaries'])} papers"
        ],
    }


async def generate_lit_review(state: ProposalState) -> dict:
    """
    Step 4: Run the literature review sub-agent.
    """
    result = await run_literature_review(
        user_id=state["user_id"],
        paper_ids=state["paper_ids"],
        focus_topic=state["topic"],
    )

    return {
        "literature_review": result["review"],
        "current_step": "literature_review",
        "steps_log": state.get("steps_log", []) + [
            f"✓ Literature review generated ({result['papers_analyzed']} papers analyzed)"
        ],
    }


async def generate_citations(state: ProposalState) -> dict:
    """
    Step 5: Run the citation sub-agent.
    """
    result = await run_citation_extraction(
        user_id=state["user_id"],
        paper_ids=state["paper_ids"],
        style="apa",
    )

    # Combine all citation texts
    citations_combined = "\n\n".join(
        r["citations_text"] for r in result["results"] if r.get("citations_text")
    )

    return {
        "citations": citations_combined,
        "current_step": "citation_extraction",
        "steps_log": state.get("steps_log", []) + [
            f"✓ Citations extracted from {result['total_papers']} papers (APA format)"
        ],
    }


async def compose_proposal(state: ProposalState) -> dict:
    """
    Step 6: Compose the final research proposal using all gathered information.
    This is the main composition step that brings everything together.
    """
    topic = state["topic"]
    topic_analysis = state.get("topic_analysis", "")
    lit_review = state.get("literature_review", "")
    citations = state.get("citations", "")

    # Build summaries text
    summaries_text = ""
    for s in state.get("summaries", []):
        if s.get("summary"):
            summaries_text += f"\n### {s.get('title', 'Paper')}\n{s['summary']}\n"

    prompt = f"""Using ALL the research materials below, compose a complete, publication-ready research proposal.

RESEARCH TOPIC: {topic}

═══════════════════════════════════════════
TOPIC ANALYSIS (from Topic Analysis Agent):
═══════════════════════════════════════════
{topic_analysis}

═══════════════════════════════════════════
PAPER SUMMARIES (from Summarization Agent):
═══════════════════════════════════════════
{summaries_text}

═══════════════════════════════════════════
LITERATURE REVIEW (from Literature Review Agent):
═══════════════════════════════════════════
{lit_review}

═══════════════════════════════════════════
EXTRACTED CITATIONS (from Citation Agent):
═══════════════════════════════════════════
{citations}

═══════════════════════════════════════════

Now compose the COMPLETE research proposal with the following structure:

# [Research Title]

## 1. Abstract
(150-250 words summarizing the entire proposal)

## 2. Introduction
### 2.1 Background
### 2.2 Problem Statement
### 2.3 Research Objectives
### 2.4 Research Questions
### 2.5 Significance of the Study

## 3. Literature Review
(Use and expand the literature review from above, properly integrated)

## 4. Research Methodology
### 4.1 Research Design
### 4.2 Data Collection Methods
### 4.3 Data Analysis Approach
### 4.4 Ethical Considerations

## 5. Expected Results and Contributions

## 6. Timeline and Work Plan

## 7. References
(Use the extracted citations, properly formatted in APA 7th edition)

IMPORTANT FORMATTING RULES:
- Use proper markdown headings and subheadings
- Use 1.5 line spacing equivalent (add blank lines between paragraphs)
- Maintain formal academic English throughout
- Each section should flow naturally into the next
- Include in-text citations where appropriate
- The proposal should be 2000-3000 words minimum"""

    proposal = await call_llm(
        prompt=prompt,
        system="""You are an expert academic proposal writer. You produce publication-quality
research proposals that follow international academic standards. Your proposals are
well-structured, thoroughly referenced, and demonstrate deep understanding of the
research landscape. Use formal academic language with proper paragraph structure.""",
        temperature=0.4,
        max_tokens=4096,
    )

    return {
        "proposal": proposal,
        "current_step": "proposal_composition",
        "steps_log": state.get("steps_log", []) + [
            "✓ Research proposal composed and formatted"
        ],
    }


async def review_proposal(state: ProposalState) -> dict:
    """
    Step 7: Quality review pass — check for coherence, completeness,
    and academic standards compliance.
    """
    proposal = state.get("proposal", "")

    prompt = f"""Review the following research proposal for quality and completeness.
Make improvements where needed:

1. Fix any formatting issues
2. Ensure all sections are present and complete
3. Improve transitions between sections
4. Verify academic tone is maintained throughout
5. Check that citations are properly referenced

PROPOSAL:
{proposal}

Return the IMPROVED and FINALIZED version of the complete proposal:"""

    reviewed = await call_llm(
        prompt=prompt,
        system="""You are a senior academic reviewer. Polish and improve the proposal
while maintaining its structure and content. Fix any gaps, improve clarity,
and ensure it meets publication standards.""",
        temperature=0.3,
        max_tokens=4096,
    )

    return {
        "proposal": reviewed,
        "status": "completed",
        "current_step": "review",
        "steps_log": state.get("steps_log", []) + [
            "✓ Quality review completed — proposal finalized"
        ],
    }


# ── Build the LangGraph ──────────────────────────────────────

def build_proposal_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph for the proposal workflow.

    Flow:
    analyze_topic → retrieve_literature → generate_summaries
        → generate_lit_review → generate_citations
        → compose_proposal → review_proposal → END
    """
    graph = StateGraph(ProposalState)

    # Add nodes
    graph.add_node("analyze_topic", analyze_topic)
    graph.add_node("retrieve_literature", retrieve_literature)
    graph.add_node("generate_summaries", generate_summaries)
    graph.add_node("generate_lit_review", generate_lit_review)
    graph.add_node("generate_citations", generate_citations)
    graph.add_node("compose_proposal", compose_proposal)
    graph.add_node("review_proposal", review_proposal)

    # Define the linear flow
    graph.set_entry_point("analyze_topic")
    graph.add_edge("analyze_topic", "retrieve_literature")
    graph.add_edge("retrieve_literature", "generate_summaries")
    graph.add_edge("generate_summaries", "generate_lit_review")
    graph.add_edge("generate_lit_review", "generate_citations")
    graph.add_edge("generate_citations", "compose_proposal")
    graph.add_edge("compose_proposal", "review_proposal")
    graph.add_edge("review_proposal", END)

    return graph


# Compile once at module level
_proposal_graph = build_proposal_graph().compile()


async def run_proposal_draft_stream(
    user_id: str,
    paper_ids: list[str],
    topic: str,
):
    """
    Execute the full proposal drafting workflow.
    Yields intermediate state updates as JSON strings to be consumed via SSE.
    """
    initial_state: ProposalState = {
        "user_id": user_id,
        "paper_ids": paper_ids,
        "topic": topic,
        "topic_analysis": "",
        "relevant_chunks": [],
        "summaries": [],
        "literature_review": "",
        "citations": "",
        "proposal": "",
        "status": "running",
        "current_step": "starting",
        "steps_log": ["⚡ Proposal generation workflow started"],
    }

    # Yield initial state
    yield json_lib.dumps({
        "type": "state_update",
        "state": {
            "current_step": initial_state["current_step"],
            "steps_log": initial_state["steps_log"],
        }
    }) + "\n"

    # Stream the graph execution and accumulate state
    final_state = dict(initial_state)
    async for output in _proposal_graph.astream(initial_state):
        # output is a dict where key is the node name that just ran, and value is the updates it returned
        for node_name, state_update in output.items():
            final_state.update(state_update)
            yield json_lib.dumps({
                "type": "state_update",
                "state": {
                    "current_step": state_update.get("current_step", node_name),
                    "steps_log": state_update.get("steps_log", []),
                }
            }) + "\n"

    yield json_lib.dumps({
        "type": "done",
        "final_result": {
            "agent": "proposal",
            "topic": topic,
            "proposal": final_state.get("proposal", ""),
            "topic_analysis": final_state.get("topic_analysis", ""),
            "literature_review": final_state.get("literature_review", ""),
            "citations": final_state.get("citations", ""),
            "summaries": final_state.get("summaries", []),
            "steps_log": final_state.get("steps_log", []),
            "status": "completed",
            "papers_used": len(paper_ids),
        }
    }) + "\n"
