from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class SimulationRequest(BaseModel):
    idea: str


class TaskStatus(BaseModel):
    task_id: str
    agent_type: str
    state: str
    dependencies: List[str]
    result: Optional[Any] = None
    error: Optional[str] = None


class SimulationResponse(BaseModel):
    run_id: str
    idea: str
    status: str
    tasks: Dict[str, TaskStatus]
    created_at: datetime


class LogEntry(BaseModel):
    timestamp: str
    agent_type: str
    event_type: str
    step: Optional[str] = None
    data: Dict[str, Any]


class RunLog(BaseModel):
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    total_events: int
    events: List[LogEntry]


class RunSummary(BaseModel):
    run_id: str
    idea: str
    status: str
    score: Optional[int] = None
    created_at: str
