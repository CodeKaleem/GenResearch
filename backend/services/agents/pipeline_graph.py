# ============================================================
# GenResearch — Pipeline Graph (14-Stage LangGraph)
# Orchestrates all nodes according to the Master Spec.
# ============================================================
from __future__ import annotations

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from services.agents.state import ProposalState
from services.agents.retry import should_retry

# Import all nodes
from services.agents.nodes.topic_input import topic_input_node
from services.agents.nodes.questionnaire import questionnaire_node
from services.agents.nodes.user_doc_quality_eval import user_doc_quality_eval_node
from services.agents.nodes.sufficiency_eval import sufficiency_eval_node
from services.agents.nodes.scrape_permission import scrape_permission_node
from services.agents.nodes.gap_report import gap_report_node
from services.agents.nodes.outline_plan import outline_plan_node
from services.agents.nodes.source_gathering import source_gathering_node
from services.agents.nodes.source_quality_eval import source_quality_eval_node
from services.agents.nodes.ingestion import ingestion_node
from services.agents.nodes.merge_ab import merge_ab_node
from services.agents.nodes.user_approval import user_approval_node
from services.agents.nodes.draft import draft_node
from services.agents.nodes.citation_verify import citation_verify_node
from services.agents.nodes.section_critic import section_critic_node
from services.agents.nodes.merge_cd import merge_cd_node
from services.agents.nodes.final_qa import final_qa_node
from services.agents.nodes.output import output_node

logger = logging.getLogger(__name__)


# ── Edge Routing Functions ───────────────────────────────────

def route_sufficiency(state: dict) -> list[str] | str:
    """Route after sufficiency_eval."""
    report = state.get("sufficiency_report", {})
    passed = report.get("overall_assessment") == "sufficient"
    feedback = "Material is insufficient. Missing background or sources."
    
    decision = should_retry(state, "sufficiency_eval", passed, feedback)
    
    if decision == "retry":
        return "sufficiency_eval" # Retry itself with feedback
    
    if passed:
        # Sufficient material: go straight to outline + ingestion (skip scraping)
        return ["outline_plan", "ingestion"]
    else:
        # Insufficient material: ask for scrape permission
        return "scrape_permission"

def route_scrape_permission(state: dict) -> list[str]:
    """Route after human-in-the-loop scrape permission."""
    granted = state.get("scrape_permission_granted", False)
    if granted:
        # User allowed scraping: run gap report -> source gathering
        return ["outline_plan", "gap_report"]
    else:
        # User denied scraping: skip gap report/source gathering, proceed with what we have
        state.setdefault("flagged_items", []).append({
            "node": "scrape_permission",
            "issue": "Scraping denied by user despite insufficient material.",
            "attempts": 1,
            "action_required": "Consider allowing scraping if draft quality is poor.",
        })
        return ["outline_plan", "ingestion"]

def route_source_quality(state: dict) -> str:
    """Route after source_quality_eval."""
    return "ingestion"

def route_citation_verify(state: dict) -> str:
    result = state.get("citation_verification_result", {})
    passed = result.get("passed", True)
    feedback = "\n".join(c.get("claim", "") for c in result.get("unverified_claims", []))
    
    decision = should_retry(state, "citation_verification", passed, feedback)
    if decision == "retry":
        return "citation_verify"
    return "merge_cd"

def route_section_critic(state: dict) -> str:
    result = state.get("section_critic_result", {})
    passed = result.get("passed", True)
    feedback = result.get("summary", "")
    
    decision = should_retry(state, "section_critic", passed, feedback)
    if decision == "retry":
        return "section_critic"
    return "merge_cd"

def route_final_qa(state: dict) -> str:
    result = state.get("final_qa_result", {})
    passed = result.get("passed", True)
    feedback = "\n".join(str(i) for i in result.get("issues", []))
    
    decision = should_retry(state, "final_qa", passed, feedback)
    if decision == "retry":
        return "final_qa"
    return "output"


# ── Build Graph ──────────────────────────────────────────────

def build_pipeline_graph() -> StateGraph:
    workflow = StateGraph(ProposalState)

    # ── Add Nodes ──
    workflow.add_node("topic_input", topic_input_node)
    workflow.add_node("questionnaire", questionnaire_node)
    workflow.add_node("user_doc_quality_eval", user_doc_quality_eval_node)
    workflow.add_node("sufficiency_eval", sufficiency_eval_node)
    workflow.add_node("scrape_permission", scrape_permission_node)
    workflow.add_node("gap_report", gap_report_node)
    workflow.add_node("outline_plan", outline_plan_node)
    workflow.add_node("source_gathering", source_gathering_node)
    workflow.add_node("source_quality_eval", source_quality_eval_node)
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("merge_ab", merge_ab_node)
    workflow.add_node("user_approval", user_approval_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("citation_verify", citation_verify_node)
    workflow.add_node("section_critic", section_critic_node)
    workflow.add_node("merge_cd", merge_cd_node)
    workflow.add_node("final_qa", final_qa_node)
    workflow.add_node("output", output_node)

    # ── Add Edges ──
    workflow.set_entry_point("topic_input")
    workflow.add_edge("topic_input", "questionnaire")
    workflow.add_edge("questionnaire", "user_doc_quality_eval")
    workflow.add_edge("user_doc_quality_eval", "sufficiency_eval")
    
    # Sufficiency Eval logic
    workflow.add_conditional_edges("sufficiency_eval", route_sufficiency, [
        "sufficiency_eval",
        "scrape_permission",
        "outline_plan",
        "ingestion"
    ])
    
    # Scrape permission logic
    workflow.add_conditional_edges("scrape_permission", route_scrape_permission, [
        "outline_plan",
        "gap_report",
        "ingestion"
    ])
    
    # Branch B flow (only runs if gap_report is hit)
    workflow.add_edge("gap_report", "source_gathering")
    workflow.add_edge("source_gathering", "source_quality_eval")
    workflow.add_conditional_edges("source_quality_eval", route_source_quality, ["ingestion"])
    
    # Fan in A & B
    workflow.add_edge("outline_plan", "merge_ab")
    workflow.add_edge("ingestion", "merge_ab")
    
    workflow.add_edge("merge_ab", "user_approval")
    workflow.add_edge("user_approval", "draft")
    
    # Fan out to Branch C & D
    workflow.add_edge("draft", "citation_verify")
    workflow.add_edge("draft", "section_critic")
    
    workflow.add_conditional_edges("citation_verify", route_citation_verify, ["citation_verify", "merge_cd"])
    workflow.add_conditional_edges("section_critic", route_section_critic, ["section_critic", "merge_cd"])
    
    # Fan in C & D
    workflow.add_edge("merge_cd", "final_qa")
    
    workflow.add_conditional_edges("final_qa", route_final_qa, ["final_qa", "output"])
    
    workflow.add_edge("output", END)

    return workflow
