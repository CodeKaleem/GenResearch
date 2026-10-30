# ============================================================
# GenResearch — Pipeline Router
# Replaces agent_tasks.py for the new 14-stage pipeline.
# ============================================================
import asyncio
import json
import logging
import uuid
from io import BytesIO
from typing import AsyncGenerator
from pathlib import Path
from zipfile import BadZipFile
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from services.agents.pipeline_graph import build_pipeline_graph
from database.supabase_client import get_supabase
from database.chroma_client import get_user_collection
from services import request_context, tracking
from services.agents.progress import get_session_queue, remove_session_queue
from services.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
MAX_QUESTIONNAIRE_FILES = 5
MAX_QUESTIONNAIRE_FILE_BYTES = 5 * 1024 * 1024
MAX_QUESTIONNAIRE_TOTAL_BYTES = 10 * 1024 * 1024
MAX_QUESTIONNAIRE_TEXT_CHARS = 100_000
QUESTIONNAIRE_FILE_TYPES = {".csv", ".docx", ".json", ".md", ".pdf", ".txt"}

# In-memory store for running pipelines (for now)
# Key: session_id, Value: {"graph": compiled_graph, "state": current_state, "thread_config": ...}
_sessions = {}


def _scale_qa_score(score) -> int | None:
    """Convert the final QA 0-10 score to the task table's 0-100 scale."""
    try:
        return round(float(score) * 10)
    except (TypeError, ValueError):
        return None


class StartPipelineRequest(BaseModel):
    user_id: str
    topic: str
    citation_style: str = "apa"
    paper_ids: list[str] = []

class SubmitQuestionnaireRequest(BaseModel):
    answers: dict


async def _extract_questionnaire_material(file: UploadFile) -> tuple[str, str, int]:
    filename = Path(file.filename or "uploaded-file").name
    extension = Path(filename).suffix.lower()
    if extension not in QUESTIONNAIRE_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for {filename}. Upload CSV, DOCX, JSON, Markdown, PDF, or TXT.",
        )

    content = await file.read(MAX_QUESTIONNAIRE_FILE_BYTES + 1)
    if len(content) > MAX_QUESTIONNAIRE_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"{filename} exceeds the 5 MB per-file limit.")

    try:
        if extension == ".pdf":
            text = await extract_text_from_pdf(content)
        elif extension == ".docx":
            document = Document(BytesIO(content))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            tables = [
                "\n".join("\t".join(cell.text for cell in row.cells) for row in table.rows)
                for table in document.tables
            ]
            text = "\n".join(part for part in [*paragraphs, *tables] if part.strip())
        else:
            text = content.decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError, OSError, BadZipFile, PackageNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not read {filename}: {exc}") from exc

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=f"No readable text was found in {filename}. Scanned PDFs need a text-based copy.",
        )
    return filename, text, len(content)


def _resume_questionnaire(session_id: str, answers: dict) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    config = _sessions[session_id]["config"]
    current_state = _pipeline_graph.get_state(config)

    if "user_doc_quality_eval" not in current_state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not awaiting questionnaire.")

    _pipeline_graph.update_state(
        config,
        {"questionnaire_answers": answers, "status": "questionnaire_answered"},
        as_node="questionnaire"
    )
    return {"status": "resumed"}


class ScrapePermissionRequest(BaseModel):
    granted: bool

class ApprovalRequest(BaseModel):
    approved: bool
    updated_outline: dict | None = None
    approval_comment: str | None = None


# Compile the graph globally
# We need checkpointer for human-in-the-loop (interrupts)
from langgraph.checkpoint.memory import MemorySaver
_checkpointer = MemorySaver()
_pipeline_graph = build_pipeline_graph().compile(
    checkpointer=_checkpointer,
    interrupt_before=[
        "user_doc_quality_eval",  # A2: Pause before checking docs, effectively pausing after questionnaire
        "scrape_permission",      # B3: Pause before web scraping
        "user_approval"           # B4: Pause before drafting
    ]
)


def _fetch_user_sources(user_id: str, paper_ids: list[str]) -> list[dict]:
    """A1 Fix: Fetch paper metadata from Supabase and content from ChromaDB."""
    if not paper_ids:
        return []

    sb = get_supabase()
    res = sb.table("papers").select("*").in_("id", paper_ids).eq("user_id", user_id).execute()
    papers = res.data or []

    col = get_user_collection(user_id)
    user_sources = []

    for p in papers:
        pid = p["id"]
        # Fetch chunks from ChromaDB for this paper
        try:
            results = col.get(where={"paper_id": pid})
            chunks = results.get("documents", [])
            content = "\n\n".join(chunks)
        except Exception:
            content = ""

        user_sources.append({
            "id": pid,
            "title": p.get("title", "Unknown Document"),
            "authors": p.get("authors", "Unknown"),
            "year": p.get("year"),
            "url": "",
            "doi": "",
            "source_type": "uploaded",
            "content": content,
            "abstract_snippet": content[:1000] if content else "",
        })

    return user_sources


@router.post("/start")
async def start_pipeline(req: StartPipelineRequest):
    """Start a new pipeline run. Executes until the first interrupt."""
    session_id = str(uuid.uuid4())
    
    # A1 Fix: Populate user_provided_sources instead of dropping paper_ids
    user_sources = _fetch_user_sources(req.user_id, req.paper_ids)
    task_id = tracking.create_task(
        req.user_id, req.topic, "proposal", paper_count=len(user_sources)
    )
    
    initial_state = {
        "topic": req.topic,
        "user_id": req.user_id,
        "session_id": session_id,
        "citation_style": req.citation_style,
        "user_provided_sources": user_sources,
        "steps_log": ["⚡ Pipeline started"]
    }
    
    thread_config = {"configurable": {"thread_id": session_id}}
    
    _sessions[session_id] = {
        "state": initial_state,
        "config": thread_config,
        "task_id": task_id,
        "stream_lock": asyncio.Lock(),
    }
    
    return {"session_id": session_id, "status": "initialized"}


@router.get("/{session_id}/stream")
async def stream_pipeline(session_id: str):
    """Stream the pipeline progress via SSE."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session_data = _sessions[session_id]
    config = session_data["config"]
    stream_lock = session_data.setdefault("stream_lock", asyncio.Lock())
    if stream_lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline stream is already active for this session.")
    await stream_lock.acquire()
    try:
        current_state = _pipeline_graph.get_state(config)
    except Exception:
        stream_lock.release()
        raise
    
    async def sse_generator() -> AsyncGenerator[str, None]:
        session_token = request_context.set_session_id(session_id)
        user_token = request_context.set_user_id(session_data["state"].get("user_id"))
        queue = get_session_queue(session_id)
        worker_error: BaseException | None = None
        worker_task: asyncio.Task | None = None

        async def astream_worker():
            nonlocal worker_error
            try:
                async for output in _pipeline_graph.astream(
                    session_data["state"] if not current_state.values else None,
                    config=config,
                    stream_mode="updates"
                ):
                    for node_name, state_update in output.items():
                        if node_name == "__interrupt__":
                            continue
                        queue.put_nowait({
                            "type": "state_update",
                            "node": node_name,
                            "state": {
                                "current_step": state_update.get("current_step", node_name),
                                "steps_log": state_update.get("steps_log", []),
                                "status": state_update.get("status", "running")
                            }
                        })
            except Exception as exc:
                worker_error = exc
            finally:
                queue.put_nowait(None)

        try:
            worker_task = asyncio.create_task(astream_worker())

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "ping"}) + "\n"
                    continue

                if item is None:
                    break
                yield json.dumps(item) + "\n"

            if worker_error is not None:
                raise worker_error

            # Check if it stopped because of an interrupt
            final_state = _pipeline_graph.get_state(config)
            next_nodes = final_state.next
            
            if "user_doc_quality_eval" in next_nodes:
                yield json.dumps({
                    "type": "interrupt",
                    "reason": "awaiting_questionnaire",
                    "questions": final_state.values.get("questionnaire_questions", [])
                }) + "\n"
            elif "scrape_permission" in next_nodes:
                yield json.dumps({
                    "type": "interrupt",
                    "reason": "awaiting_scrape_permission"
                }) + "\n"
            elif "user_approval" in next_nodes:
                yield json.dumps({
                    "type": "interrupt",
                    "reason": "awaiting_approval",
                    "outline": final_state.values.get("outline", {}),
                    "sources": final_state.values.get("citation_registry", [])
                }) + "\n"
            elif not next_nodes:
                 final_values = final_state.values
                 qa_score = _scale_qa_score(
                     final_values.get("final_qa_result", {}).get("overall_score")
                 )
                 tracking.complete_task(session_data.get("task_id"), "completed", qa_score)
                 if final_values.get("draft_text"):
                     tracking.save_task_result(
                         task_id=session_data.get("task_id"),
                         user_id=session_data["state"].get("user_id", ""),
                         type_="proposal",
                         title=session_data["state"].get("topic", "Research proposal"),
                         content=final_values["draft_text"],
                         score=qa_score,
                     )
                 tracking.log_agent_event(
                     "success", "Proposal pipeline completed.",
                     agent="proposal", user_id=session_data["state"].get("user_id")
                 )
                 yield json.dumps({
                    "type": "done",
                    "final_state": {
                        "draft_file_path": final_values.get("draft_file_path"),
                        "completion_guide_file_path": final_values.get("completion_guide_file_path"),
                    }
                }) + "\n"
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            tracking.complete_task(session_data.get("task_id"), "failed")
            tracking.log_agent_event(
                "error", f"Proposal pipeline failed: {str(e)[:1800]}",
                agent="proposal", user_id=session_data["state"].get("user_id")
            )
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            remove_session_queue(session_id)
            if worker_task and not worker_task.done():
                worker_task.cancel()
            request_context.reset_user_id(user_token)
            request_context.reset_session_id(session_token)
            stream_lock.release()

    return StreamingResponse(sse_generator(), media_type="application/x-ndjson")


@router.post("/{session_id}/questionnaire")
async def submit_questionnaire(session_id: str, req: SubmitQuestionnaireRequest):
    """Resume the pipeline after questionnaire checkpoint."""
    return _resume_questionnaire(session_id, req.answers)


@router.post("/{session_id}/questionnaire/with-files")
async def submit_questionnaire_with_files(
    session_id: str,
    answers: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """Resume the questionnaire with optional reference materials."""
    try:
        parsed_answers = json.loads(answers)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Questionnaire answers must be valid JSON.") from exc
    if not isinstance(parsed_answers, dict):
        raise HTTPException(status_code=400, detail="Questionnaire answers must be a JSON object.")
    if len(files) > MAX_QUESTIONNAIRE_FILES:
        raise HTTPException(status_code=400, detail="You can attach up to 5 files.")

    materials = []
    total_bytes = 0
    for file in files:
        filename, text, file_size = await _extract_questionnaire_material(file)
        total_bytes += file_size
        if total_bytes > MAX_QUESTIONNAIRE_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="Attached files exceed the 10 MB total limit.")
        materials.append(f"--- {filename} ---\n{text}")

    if materials:
        material_text = "\n\n".join(materials)
        parsed_answers["uploaded_materials"] = material_text[:MAX_QUESTIONNAIRE_TEXT_CHARS]
        if len(material_text) > MAX_QUESTIONNAIRE_TEXT_CHARS:
            parsed_answers["uploaded_materials"] += "\n[Attachment text truncated to fit the research workflow.]"

    return _resume_questionnaire(session_id, parsed_answers)


@router.post("/{session_id}/scrape-permission")
async def grant_scrape_permission(session_id: str, req: ScrapePermissionRequest):
    """Resume the pipeline after scrape permission checkpoint."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    config = _sessions[session_id]["config"]
    current_state = _pipeline_graph.get_state(config)
    
    if "scrape_permission" not in current_state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not awaiting scrape permission.")
    
    _pipeline_graph.update_state(
        config,
        {"scrape_permission_granted": req.granted, "status": "permission_resolved"},
        as_node="sufficiency_eval"
    )
    
    return {"status": "resumed"}


@router.post("/{session_id}/approve")
async def approve_pipeline(session_id: str, req: ApprovalRequest):
    """Resume the pipeline after user approval checkpoint."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    config = _sessions[session_id]["config"]
    current_state = _pipeline_graph.get_state(config)
    
    if "user_approval" not in current_state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not awaiting approval.")
    
    state_updates = {"status": "approved"}
    if req.updated_outline:
        state_updates["outline"] = req.updated_outline
    if req.approval_comment:
        state_updates["approval_comment"] = req.approval_comment

    # Resume from the interrupted node's direct predecessor. Starting from
    # merge_ab re-runs context_build and hits the user_approval interrupt again.
    _pipeline_graph.update_state(config, state_updates, as_node="context_build")
    
    return {"status": "resumed"}
