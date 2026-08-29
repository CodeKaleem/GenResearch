# ============================================================
# GenResearch — Pipeline Router
# Replaces agent_tasks.py for the new 14-stage pipeline.
# ============================================================
import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.agents.pipeline_graph import build_pipeline_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# In-memory store for running pipelines (for now)
# Key: session_id, Value: {"graph": compiled_graph, "state": current_state, "thread_config": ...}
_sessions = {}


class StartPipelineRequest(BaseModel):
    user_id: str
    topic: str
    citation_style: str = "apa"
    paper_ids: list[str] = []

class SubmitQuestionnaireRequest(BaseModel):
    answers: dict

class ApprovalRequest(BaseModel):
    approved: bool
    updated_outline: dict | None = None


# Compile the graph globally
# We need checkpointer for human-in-the-loop (interrupts)
from langgraph.checkpoint.memory import MemorySaver
_checkpointer = MemorySaver()
_pipeline_graph = build_pipeline_graph().compile(
    checkpointer=_checkpointer,
    interrupt_before=["user_approval"]
)


@router.post("/start")
async def start_pipeline(req: StartPipelineRequest):
    """Start a new pipeline run. Executes until the first interrupt (User Approval)."""
    import uuid
    session_id = str(uuid.uuid4())
    
    initial_state = {
        "topic": req.topic,
        "user_id": req.user_id,
        "session_id": session_id,
        "citation_style": req.citation_style,
        "steps_log": ["⚡ Pipeline started"]
    }
    
    thread_config = {"configurable": {"thread_id": session_id}}
    
    # Start it asynchronously so we can return the session ID immediately
    # In a real production app, this would go to Celery/Redis queue.
    # For now, we'll let the user stream it.
    
    _sessions[session_id] = {
        "state": initial_state,
        "config": thread_config
    }
    
    return {"session_id": session_id, "status": "initialized"}


@router.get("/{session_id}/stream")
async def stream_pipeline(session_id: str):
    """Stream the pipeline progress via SSE."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session_data = _sessions[session_id]
    config = session_data["config"]
    
    # Determine if we need to resume or start fresh
    current_state = _pipeline_graph.get_state(config)
    
    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            # We use astream to yield updates
            async for output in _pipeline_graph.astream(
                session_data["state"] if not current_state.values else None, 
                config=config,
                stream_mode="updates"
            ):
                for node_name, state_update in output.items():
                    if node_name == "__interrupt__":
                        continue
                        
                    yield json.dumps({
                        "type": "state_update",
                        "node": node_name,
                        "state": {
                            "current_step": state_update.get("current_step", node_name),
                            "steps_log": state_update.get("steps_log", []),
                            "status": state_update.get("status", "running")
                        }
                    }) + "\n"
            
            # Check if it stopped because of an interrupt
            final_state = _pipeline_graph.get_state(config)
            next_nodes = final_state.next
            
            if "user_approval" in next_nodes:
                yield json.dumps({
                    "type": "interrupt",
                    "reason": "awaiting_approval",
                    "outline": final_state.values.get("outline", {}),
                    "sources": final_state.values.get("citation_registry", [])
                }) + "\n"
            elif not next_nodes:
                 yield json.dumps({
                    "type": "done",
                    "final_state": {
                        "draft_file_path": final_state.values.get("draft_file_path"),
                        "completion_guide_file_path": final_state.values.get("completion_guide_file_path"),
                    }
                }) + "\n"
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(sse_generator(), media_type="application/x-ndjson")


@router.post("/{session_id}/questionnaire")
async def submit_questionnaire(session_id: str, req: SubmitQuestionnaireRequest):
    """Submit questionnaire answers. Since we don't interrupt here in LangGraph strictly,
    we can just update the state and resume streaming."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    config = _sessions[session_id]["config"]
    
    _pipeline_graph.update_state(
        config,
        {"questionnaire_answers": req.answers},
        as_node="topic_input"
    )
    
    return {"status": "answers_submitted"}


@router.post("/{session_id}/approve")
async def approve_pipeline(session_id: str, req: ApprovalRequest):
    """Resume the pipeline after user approval checkpoint."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    config = _sessions[session_id]["config"]
    current_state = _pipeline_graph.get_state(config)
    
    if "user_approval" not in current_state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not awaiting approval.")
    
    # Update state if user modified the outline
    state_updates = {"status": "approved"}
    if req.updated_outline:
        state_updates["outline"] = req.updated_outline
        
    _pipeline_graph.update_state(config, state_updates, as_node="merge_ab")
    
    return {"status": "resumed"}
