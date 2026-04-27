from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from typing import List, Dict, Any
import os
import json
import uuid
from datetime import datetime

from app.api.schemas import SimulationRequest, SimulationResponse, RunSummary, RunLog
from app.services.run_manager import RunManager
from app.orchestrator.scheduler import Scheduler
from app.core.telemetry import get_telemetry
from app.agents.guardrails import validate_idea
from app.memory.db import save_run, get_run, list_runs as list_runs_db
from app.evaluation.trace_exporter import TraceExporter


router = APIRouter()

# In-memory store for active runs (for real-time status)
ACTIVE_RUNS: Dict[str, Any] = {}


@router.post("/simulate", response_model=Dict[str, str])
async def start_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    # 1. Guardrail Validation
    validation = await validate_idea(request.idea)
    if not validation.is_valid:
        raise HTTPException(status_code=400, detail=validation.reason or "Invalid startup idea")
        
    idea = validation.cleansed_idea or request.idea
    run_id = str(uuid.uuid4())
    
    # 2. Historical Context (Iteration)
    parent_results = None
    iteration = 1
    if request.parent_run_id:
        parent_run = await get_run(request.parent_run_id)
        if parent_run:
            # DB results blob contains the full simulation result from RunManager
            # The context is under the 'results' or 'final_context' key
            p_results_blob = parent_run.get("results") or {}
            parent_results = p_results_blob.get("results") or p_results_blob.get("final_context") or {}
            
            # Fallback if the above both fail (unlikely but safe)
            if not parent_results and "market_analysis" in p_results_blob:
                 parent_results = p_results_blob
            
            iteration = (parent_run.get("iteration") or 1) + 1

    # Pre-initialize telemetry so the frontend can discover it immediately
    get_telemetry(run_id, idea=request.idea)
    
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "idea": idea,
        "status": "pending",
        "iteration": iteration,
        "parent_run_id": request.parent_run_id,
        "feedback": request.feedback,
        "created_at": datetime.now().isoformat(),
        "context": {}
    }
    
    # Save initial state to DB
    await save_run(
        run_id, 
        idea, 
        "pending", 
        parent_run_id=request.parent_run_id, 
        iteration=iteration, 
        feedback=request.feedback
    )
    
    # ── Simulation worker ───────────
    async def run_task(idea: str, run_id: str, parent_results: dict, feedback: str, iteration: int):
        try:
            ACTIVE_RUNS[run_id]["status"] = "running"
            
            # --- Telemetry Continuity: Seed with parent logs ---
            telemetry = get_telemetry(run_id, idea=idea)
            if request.parent_run_id:
                try:
                    parent_log_path = f"logs/{request.parent_run_id}.json"
                    if os.path.exists(parent_log_path):
                        with open(parent_log_path, "r") as f:
                            parent_data = json.load(f)
                            if "events" in parent_data:
                                telemetry.seed_events(parent_data["events"])
                                print(f"TELEMETRY: Inherited {len(parent_data['events'])} events from parent {request.parent_run_id}")
                except Exception as te:
                    print(f"TELEMETRY: Failed to inherit logs: {te}")
            # --------------------------------------------------

            await save_run(
                run_id, idea, "running", 
                parent_run_id=request.parent_run_id, 
                iteration=iteration, 
                feedback=feedback
            )
            
            result = await RunManager.run_simulation(
                idea, 
                run_id=run_id, 
                parent_results=parent_results, 
                feedback=feedback
            )
            
            # Ensure context is JSON serializable for DB storage.
            # This prevents Pydantic objects from causing double-encoding or crashes.
            raw_context = result.get("final_context", {})
            serializable_context = {}
            for k, v in raw_context.items():
                if hasattr(v, "dict"):
                    serializable_context[k] = v.dict()
                elif hasattr(v, "model_dump"):
                    serializable_context[k] = v.model_dump()
                elif isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                    serializable_context[k] = v
                else:
                    # Fallback for complex non-pydantic objects
                    try:
                        serializable_context[k] = json.loads(json.dumps(v, default=str))
                    except:
                        serializable_context[k] = str(v)
            
            # Update the result object so the clean context is saved
            result["final_context"] = serializable_context
            
            
            ACTIVE_RUNS[run_id]["context"] = serializable_context
            ACTIVE_RUNS[run_id]["status"] = "completed"
            
            # Extract score for DB
            scorecard = serializable_context.get("evaluation_scorecard", {})
            score = scorecard.get("total_score") if isinstance(scorecard, dict) else None
            
            await save_run(
                run_id, idea, "completed", 
                results=result, score=score,
                parent_run_id=request.parent_run_id,
                iteration=iteration,
                feedback=feedback
            )
        except Exception as e:
            ACTIVE_RUNS[run_id]["status"] = "failed"
            ACTIVE_RUNS[run_id]["error"] = str(e)
            await save_run(
                run_id, idea, "failed", 
                results={"error": str(e)},
                parent_run_id=request.parent_run_id,
                iteration=iteration,
                feedback=feedback
            )
            print(f"SIMULATION ERROR ({run_id}):", e)

    background_tasks.add_task(run_task, idea, run_id, parent_results, request.feedback, iteration)
    
    return {"run_id": run_id}


@router.get("/run/{run_id}", response_model=Dict[str, Any])
async def get_run_status(run_id: str):
    # 1. Check active runs first (for real-time status)
    if run_id in ACTIVE_RUNS:
        run_data = ACTIVE_RUNS[run_id]
        context  = run_data.get("context", {})
        return {
            **run_data,
            "results": {
                "idea":          run_data.get("idea"),
                "final_context": context,
            },
            "iteration":     run_data.get("iteration", 1),
            "feedback":      run_data.get("feedback"),
            "quality_flags": context.get("quality_flags"),
        }
        
    # 2. Check Database (Neon)
    db_run = await get_run(run_id)
    if db_run:
        # Unify format
        results = db_run.get("results") or {}
        return {
            "run_id": str(db_run["run_id"]),
            "idea": db_run["idea"],
            "status": db_run["status"],
            "created_at": db_run["created_at"].isoformat() if hasattr(db_run["created_at"], "isoformat") else db_run["created_at"],
            "results": results or {
                "idea": db_run["idea"],
                "final_context": {}
            }
        }

    # 3. Fallback to filesystem
    log_path = f"logs/{run_id}.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log_data = json.load(f)
            return {
                "run_id": run_id,
                "idea": log_data.get("idea", "Unknown"),
                "status": "completed",
                "results": log_data
            }

    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/run/{run_id}/logs")
async def get_run_logs(run_id: str):
    # 1. Try to get active logs from memory first
    # We check the global registry directly to see if it's currently being tracked
    from app.core.telemetry import _telemetry_instances
    
    if run_id in _telemetry_instances:
        telemetry = _telemetry_instances[run_id]
        return {
            "run_id": run_id,
            "events": telemetry.events,
            "status": ACTIVE_RUNS.get(run_id, {}).get("status", "running")
        }

    # 2. If not in memory, check the filesystem
    log_path = f"logs/{run_id}.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
            
    raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/run/{run_id}/export")
async def export_run_traces(run_id: str, format: str = "json"):
    """
    Export per-agent reasoning traces for a completed run.

    Query params:
      - format=json   (default) — structured JSON with metadata + trace array
      - format=jsonl  — JSONL, one record per agent (SFT/RLHF ready)

    Each trace record contains:
      - agent identity & run metadata
      - reconstructed message thread (system → user → assistant)
      - parsed structured output
      - quality gate result (structural validation per field)
      - token usage aggregated across the agent's full loop
      - human_label / human_rating / human_comment slots (null until feedback is posted)
    """
    # Resolve context + telemetry from active memory or filesystem log
    context = None
    telemetry = None

    # 1. Active run in memory
    if run_id in ACTIVE_RUNS:
        run_data = ACTIVE_RUNS[run_id]
        if run_data.get("status") != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Run '{run_id}' is not yet completed (status: {run_data.get('status')}). "
                       "Wait for the simulation to finish before exporting traces."
            )
        context = run_data.get("context", {})

    # 2. Filesystem log fallback
    if context is None:
        log_path = f"logs/{run_id}.json"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_data = json.load(f)
            context = log_data.get("final_context") or {}
        else:
            raise HTTPException(status_code=404, detail="Run not found or log file missing")

    # Ensure quality flags are populated (idempotent if already set)
    if "quality_flags" not in context:
        from app.evaluation.quality_gates import run_all_quality_gates
        run_all_quality_gates(context)

    exporter = TraceExporter(run_id=run_id, context=context, telemetry=telemetry)

    if format == "jsonl":
        jsonl_content = exporter.export_jsonl()
        return Response(
            content=jsonl_content,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="traces_{run_id}.jsonl"'},
        )

    # Default: structured JSON
    return exporter.export_dict()


@router.get("/runs", response_model=List[RunSummary])
async def list_runs():
    # 1. Fetch from Database (Neon) - Primary Source
    db_runs = await list_runs_db() # renamed to avoid conflict
    
    # 2. Collect Active Runs
    active_ids = set(ACTIVE_RUNS.keys())
    
    runs_map = {}
    
    # Add DB runs
    for r in db_runs:
        runs_map[str(r['run_id'])] = RunSummary(
            run_id=str(r['run_id']),
            idea=r['idea'],
            status=r['status'],
            score=r['score'],
            parent_run_id=str(r['parent_run_id']) if r.get('parent_run_id') else None,
            iteration=r.get('iteration', 1),
            feedback=r.get('feedback'),
            created_at=r['created_at'].isoformat() if hasattr(r['created_at'], "isoformat") else r['created_at']
        )
        
    # Overlay/Add Active Runs
    for run_id, run_data in ACTIVE_RUNS.items():
        score = None
        context = run_data.get("context", {})
        scorecard = context.get("evaluation_scorecard", {})
        if isinstance(scorecard, dict):
            score = scorecard.get("total_score")
            
        runs_map[run_id] = RunSummary(
            run_id=run_id,
            idea=run_data.get("idea", "Unknown"),
            status=run_data.get("status", "pending"),
            score=score,
            parent_run_id=run_data.get("parent_run_id"),
            iteration=run_data.get("iteration", 1),
            feedback=run_data.get("feedback"),
            created_at=run_data.get("created_at", datetime.now().isoformat())
        )

    # 3. Final list sorted by date
    final_runs = list(runs_map.values())
    final_runs.sort(key=lambda x: x.created_at, reverse=True)
    return final_runs
