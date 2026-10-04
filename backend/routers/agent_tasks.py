# ============================================================
# GenResearch — Agent Tasks Router
# API endpoints for all 4 research agents
# ============================================================
import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.agents.summarization_agent import run_summarization
from services.agents.literature_review_agent import run_literature_review
from services.agents.citation_agent import run_citation_extraction
from services.agents.proposal_graph import run_proposal_draft_stream
from services import request_context, tracking

router = APIRouter(prefix="/agents", tags=["agents"])
TASK_RESULT_TYPES = {"summarization": "summary", "literature_review": "review"}


async def _run_tracked_agent(user_id: str, title: str, agent_type: str, paper_ids: list[str], run):
    """Run an agent while persisting best-effort task, result, and log records."""
    task_id = tracking.create_task(user_id, title, agent_type, len(paper_ids))
    user_token = request_context.set_user_id(user_id)
    try:
        result = await run()
        tracking.complete_task(task_id, "completed")
        tracking.save_task_result(
            task_id=task_id,
            user_id=user_id,
            type_=TASK_RESULT_TYPES.get(agent_type, agent_type),
            title=title,
            content=json.dumps(result, ensure_ascii=False, default=str),
        )
        tracking.log_agent_event(
            "success", f"Completed {title} for {len(paper_ids)} paper(s).", agent=agent_type, user_id=user_id
        )
        return result
    except Exception as error:
        tracking.complete_task(task_id, "failed")
        tracking.log_agent_event(
            "error", f"{title} failed: {str(error)[:1800]}", agent=agent_type, user_id=user_id
        )
        raise
    finally:
        request_context.reset_user_id(user_token)


# ── Request Models ────────────────────────────────────────────

class AgentRequest(BaseModel):
    user_id: str
    paper_ids: list[str]


class LitReviewRequest(BaseModel):
    user_id: str
    paper_ids: list[str]
    focus_topic: str = ""


class CitationRequest(BaseModel):
    user_id: str
    paper_ids: list[str]
    style: str = "apa"  # apa, mla, ieee, chicago


class ProposalRequest(BaseModel):
    user_id: str
    paper_ids: list[str]
    topic: str


# ── POST /agents/summarize ────────────────────────────────────

@router.post("/summarize")
async def summarize_papers(req: AgentRequest):
    """
    Summarize one or more papers.
    Returns structured summaries with key findings, methodology, and conclusions.
    """
    if not req.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper_id is required.")
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")

    try:
        result = await _run_tracked_agent(
            user_id=req.user_id,
            title="Paper summarization",
            agent_type="summarization",
            paper_ids=req.paper_ids,
            run=lambda: run_summarization(user_id=req.user_id, paper_ids=req.paper_ids),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")


# ── POST /agents/literature-review ────────────────────────────

@router.post("/literature-review")
async def literature_review(req: LitReviewRequest):
    """
    Generate a comparative literature review from multiple papers.
    Optionally focuses on a specific topic.
    """
    if not req.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper_id is required.")
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")

    try:
        result = await _run_tracked_agent(
            user_id=req.user_id,
            title=req.focus_topic or "Literature review",
            agent_type="literature_review",
            paper_ids=req.paper_ids,
            run=lambda: run_literature_review(
                user_id=req.user_id,
                paper_ids=req.paper_ids,
                focus_topic=req.focus_topic,
            ),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Literature review failed: {e}")


# ── POST /agents/citations ───────────────────────────────────

@router.post("/citations")
async def extract_citations(req: CitationRequest):
    """
    Extract and format citations from papers.
    Supports APA, MLA, IEEE, and Chicago styles.
    """
    if not req.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper_id is required.")
    if req.style.lower() not in ("apa", "mla", "ieee", "chicago"):
        raise HTTPException(status_code=400, detail="Style must be: apa, mla, ieee, or chicago.")

    try:
        result = await _run_tracked_agent(
            user_id=req.user_id,
            title=f"Citation extraction ({req.style.upper()})",
            agent_type="citation",
            paper_ids=req.paper_ids,
            run=lambda: run_citation_extraction(
                user_id=req.user_id,
                paper_ids=req.paper_ids,
                style=req.style,
            ),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citation extraction failed: {e}")


# ── POST /agents/proposal ────────────────────────────────────
#
# @router.post("/proposal")
# async def draft_proposal(req: ProposalRequest):
#     """
#     Draft a complete research proposal using LangGraph orchestration.
#     Invokes all sub-agents (summarization, literature review, citation)
#     and composes a publication-ready proposal.
#     """
#     if not req.paper_ids:
#         raise HTTPException(status_code=400, detail="At least one paper_id is required.")
#     if not req.topic.strip():
#         raise HTTPException(status_code=400, detail="Research topic is required.")
#
#     try:
#         # result = await run_proposal_draft(
#         #     user_id=req.user_id,
#         #     paper_ids=req.paper_ids,
#         #     topic=req.topic,
#         # )
#         # return result
#         raise NotImplementedError("run_proposal_draft is not implemented.")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Proposal drafting failed: {e}")

# ── POST /agents/proposal-stream ────────────────────────────

@router.post("/proposal-stream")
async def draft_proposal_stream(req: ProposalRequest):
    """
    Draft a complete research proposal using LangGraph orchestration.
    Streams intermediate states via SSE.
    """
    if not req.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper_id is required.")
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Research topic is required.")

    async def tracked_proposal_stream():
        task_id = tracking.create_task(
            req.user_id, req.topic, "proposal", paper_count=len(req.paper_ids)
        )
        user_token = request_context.set_user_id(req.user_id)
        session_token = request_context.set_session_id(str(uuid.uuid4()))
        final_result = None
        try:
            async for line in run_proposal_draft_stream(
                user_id=req.user_id,
                paper_ids=req.paper_ids,
                topic=req.topic,
            ):
                try:
                    event = json.loads(line)
                    if event.get("type") == "done":
                        final_result = event.get("final_result")
                except (TypeError, json.JSONDecodeError):
                    pass
                yield line

            tracking.complete_task(task_id, "completed")
            if final_result:
                tracking.save_task_result(
                    task_id=task_id,
                    user_id=req.user_id,
                    type_="proposal",
                    title=req.topic,
                    content=json.dumps(final_result, ensure_ascii=False, default=str),
                )
            tracking.log_agent_event(
                "success",
                f"Completed proposal drafting for {len(req.paper_ids)} paper(s).",
                agent="proposal",
                user_id=req.user_id,
            )
        except Exception as error:
            tracking.complete_task(task_id, "failed")
            tracking.log_agent_event(
                "error", f"Proposal drafting failed: {str(error)[:1800]}",
                agent="proposal", user_id=req.user_id,
            )
            raise
        finally:
            request_context.reset_session_id(session_token)
            request_context.reset_user_id(user_token)

    return StreamingResponse(tracked_proposal_stream(), media_type="application/x-ndjson")


# ── POST /agents/cancel ──────────────────────────────────────

class CancelRequest(BaseModel):
    user_id: str
    task_id: str = ""


@router.post("/cancel")
async def cancel_agent_task(req: CancelRequest):
    """
    Cancel an active agent task.
    """
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")

    try:
        from database.supabase_client import get_supabase
        sb = get_supabase()
        if req.task_id:
            sb.table("tasks").update({"status": "failed"}).eq("id", req.task_id).execute()
        else:
            sb.table("tasks").update({"status": "failed"}).eq("user_id", req.user_id).eq("status", "processing").execute()
    except Exception:
        pass

    return {"status": "cancelled", "task_id": req.task_id, "user_id": req.user_id}

