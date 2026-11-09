import os
import json
import uuid
import asyncio
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langgraph.types import Command
from agent.state import AgentState
from agent.graph import build_safety_agent_graph, get_default_checkpointer

router = APIRouter(prefix="/api")

# In-memory storage for active runs and persistent graph checkpointer
RUNS: Dict[str, Dict[str, Any]] = {}
CHECKPOINTER = get_default_checkpointer()
GRAPH = build_safety_agent_graph(checkpointer=CHECKPOINTER)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

class RunCreateRequest(BaseModel):
    drug: str = Field(..., min_length=1, description="Name of the pharmaceutical drug to investigate")

class ReviewRequest(BaseModel):
    action: str = Field(..., description="Action to take: approve, edit, or investigate_more")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)

def save_run_to_file(run_id: str, run_data: Dict[str, Any]):
    """Persist run execution log and final results to JSON file."""
    try:
        path = os.path.join(DATA_DIR, f"run_{run_id}.json")
        cleaned_data = {k: v for k, v in run_data.items() if k != "event_notify"}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving run file for {run_id}: {e}")

async def broadcast_event(run_id: str, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
    """Enqueue an event for SSE broadcasting and notify waiting streams."""
    evt = {
        "run_id": run_id,
        "event_type": event_type,
        "message": message,
        "data": data or {},
        "timestamp": time.time()
    }
    if run_id in RUNS:
        RUNS[run_id]["events"].append(evt)
        notify = RUNS[run_id].get("event_notify")
        if notify:
            notify.set()

async def execute_graph_run(run_id: str, initial_state: Optional[AgentState] = None, resume_command: Optional[Command] = None):
    """Execute or resume graph processing in background with event streaming."""
    config = {"configurable": {"thread_id": run_id}}
    try:
        if resume_command is not None:
            await broadcast_event(run_id, "node_start", "Resuming workflow after human review...", {})
            input_val = resume_command
        else:
            await broadcast_event(run_id, "node_start", f"Workflow started for drug '{initial_state.drug}'", {})
            input_val = initial_state.model_dump()

        # Stream graph steps
        prev_event_count = 0
        async for output_step in GRAPH.astream(input_val, config=config, stream_mode="updates"):
            # Inspect new events emitted by the active node
            snapshot = GRAPH.get_state(config)
            state_vals = snapshot.values
            events = state_vals.get("events", [])
            
            # Broadcast any newly added state events sequentially
            while prev_event_count < len(events):
                ev = events[prev_event_count]
                await broadcast_event(run_id, ev.get("event_type", "node_step"), ev.get("message", ""), ev.get("data", {}))
                prev_event_count += 1

            # Update cached run state
            RUNS[run_id]["state"] = state_vals
            if "evidence" in state_vals:
                RUNS[run_id]["evidence"] = {k: (v.model_dump() if hasattr(v, "model_dump") else v) for k, v in state_vals["evidence"].items()}
            if "structured_assessment" in state_vals and state_vals["structured_assessment"]:
                sa = state_vals["structured_assessment"]
                RUNS[run_id]["assessment"] = sa.model_dump() if hasattr(sa, "model_dump") else sa
            if "draft" in state_vals:
                RUNS[run_id]["draft"] = state_vals["draft"]

        # Check if state recorded an error (e.g. drug not found) or paused at interrupt
        snapshot = GRAPH.get_state(config)
        state_vals = snapshot.values

        if state_vals.get("error"):
            RUNS[run_id]["status"] = "not_found"
            RUNS[run_id]["error"] = state_vals["error"]
            await broadcast_event(run_id, "error", state_vals["error"], {"error": state_vals["error"], "drug": RUNS[run_id].get("drug")})
            save_run_to_file(run_id, RUNS[run_id])
            return

        if snapshot.next and "human_review" in snapshot.next:
            RUNS[run_id]["status"] = "needs_review"
            await broadcast_event(run_id, "interrupt", "Graph paused at Human Review gate. Awaiting clinician/user action.", {
                "needs_review": True,
                "evidence": RUNS[run_id].get("evidence", {}),
                "draft": RUNS[run_id].get("draft", "")
            })
        else:
            RUNS[run_id]["status"] = "completed"
            await broadcast_event(run_id, "final", "Safety investigation completed successfully.", {
                "assessment": RUNS[run_id].get("assessment", {}),
                "evidence": RUNS[run_id].get("evidence", {}),
                "draft": RUNS[run_id].get("draft", "")
            })
            save_run_to_file(run_id, RUNS[run_id])

    except Exception as e:
        RUNS[run_id]["status"] = "error"
        RUNS[run_id]["error"] = str(e)
        await broadcast_event(run_id, "error", f"Investigation failed with error: {str(e)}", {"error": str(e)})
        save_run_to_file(run_id, RUNS[run_id])

@router.post("/runs")
async def create_run(req: RunCreateRequest, background_tasks: BackgroundTasks):
    """Start a new drug safety investigation run."""
    run_id = str(uuid.uuid4())
    notify = asyncio.Event()

    initial_state = AgentState(
        drug=req.drug,
        run_id=run_id
    )

    RUNS[run_id] = {
        "run_id": run_id,
        "drug": req.drug,
        "status": "running",
        "created_at": time.time(),
        "events": [],
        "event_notify": notify,
        "evidence": {},
        "draft": "",
        "assessment": None,
        "state": initial_state.model_dump()
    }

    # Launch graph background execution
    background_tasks.add_task(execute_graph_run, run_id, initial_state)

    return {
        "run_id": run_id,
        "drug": req.drug,
        "status": "started",
        "events_url": f"/api/runs/{run_id}/events"
    }

@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    """Server-Sent Events (SSE) stream of investigation progress, tool calls, critic reviews, and findings."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run ID not found.")

    async def event_generator():
        sent_index = 0
        run_info = RUNS.get(run_id)
        if not run_info:
            return

        notify = run_info.get("event_notify")

        while True:
            if await request.is_disconnected():
                break

            events = run_info.get("events", [])
            # Sequentially emit unread events without duplication
            while sent_index < len(events):
                evt = events[sent_index]
                sent_index += 1
                yield f"event: {evt['event_type']}\ndata: {json.dumps(evt)}\n\n"
                if evt.get("event_type") in ("final", "error"):
                    return

            if notify:
                notify.clear()
                try:
                    await asyncio.wait_for(notify.wait(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
            else:
                await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/runs/{run_id}/review")
async def submit_human_review(run_id: str, review: ReviewRequest, background_tasks: BackgroundTasks):
    """Submit human review action (approve, edit, investigate_more) to resume interrupted graph."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run ID not found.")
    
    if RUNS[run_id].get("status") != "needs_review":
        return {"status": RUNS[run_id].get("status"), "message": "Run is not paused for review."}

    RUNS[run_id]["status"] = "resuming"
    resume_cmd = Command(resume={
        "action": review.action,
        "payload": review.payload
    })

    # Resume graph execution in background
    background_tasks.add_task(execute_graph_run, run_id, None, resume_cmd)

    return {
        "run_id": run_id,
        "action": review.action,
        "status": "resumed"
    }

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Retrieve full status, structured assessment, and evidence for a run."""
    if run_id not in RUNS:
        path = os.path.join(DATA_DIR, f"run_{run_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="Run ID not found.")
    
    cleaned_data = {k: v for k, v in RUNS[run_id].items() if k != "event_notify"}
    return cleaned_data
