from fastapi import APIRouter, HTTPException, BackgroundTasks
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
    
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "idea": idea,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "context": {}
    }
    
    # Save initial state to DB
    await save_run(run_id, idea, "pending")
    
    # ── Simulation worker ───────────
    async def run_task(idea: str, run_id: str):
        try:
            ACTIVE_RUNS[run_id]["status"] = "running"
            await save_run(run_id, idea, "running")
            
            result = await RunManager.run_simulation(idea, run_id=run_id)
            
            # Ensure context is JSON serializable
            raw_context = result.get("results", {})
            serializable_context = {}
            for k, v in raw_context.items():
                if hasattr(v, "dict"):
                    serializable_context[k] = v.dict()
                elif hasattr(v, "model_dump"): # For newer Pydantic versions
                    serializable_context[k] = v.model_dump()
                else:
                    serializable_context[k] = v
            
            
            ACTIVE_RUNS[run_id]["context"] = serializable_context
            ACTIVE_RUNS[run_id]["status"] = "completed"
            
            # Extract score for DB
            scorecard = serializable_context.get("evaluation_scorecard", {})
            score = scorecard.get("total_score") if isinstance(scorecard, dict) else None
            
            await save_run(run_id, idea, "completed", results=result, score=score)
        except Exception as e:
            ACTIVE_RUNS[run_id]["status"] = "failed"
            ACTIVE_RUNS[run_id]["error"] = str(e)
            await save_run(run_id, idea, "failed", results={"error": str(e)})
            print(f"SIMULATION ERROR ({run_id}):", e)

    background_tasks.add_task(run_task, request.idea, run_id)
    
    return {"run_id": run_id}


@router.get("/run/{run_id}", response_model=Dict[str, Any])
async def get_run_status(run_id: str):
    # 1. Check active runs first (for real-time status)
    if run_id in ACTIVE_RUNS:
        run_data = ACTIVE_RUNS[run_id]
        return {
            **run_data,
            "results": {
                "idea": run_data.get("idea"),
                "final_context": run_data.get("context", {})
            }
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
    telemetry = get_telemetry(run_id)
    if telemetry and telemetry.events:
        return {
            "run_id": run_id,
            "events": telemetry.events,
            "status": ACTIVE_RUNS.get(run_id, {}).get("status", "unknown")
        }

    # 2. If not in memory, check the filesystem
    log_path = f"logs/{run_id}.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
            
    raise HTTPException(status_code=404, detail="Log file not found")


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
            created_at=run_data.get("created_at", datetime.now().isoformat())
        )

    # 3. Final list sorted by date
    final_runs = list(runs_map.values())
    final_runs.sort(key=lambda x: x.created_at, reverse=True)
    return final_runs
