import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


from app.core.llm_config import DEFAULT_MODEL, MODEL_PRICING

class TelemetryManager:
    """
    Manages logging and telemetry for agent simulation runs.
    Logs are stored in memory during the run and persisted to JSON files.
    """

    def __init__(self, run_id: Optional[str] = None, idea: str = "Unknown", log_dir: str = "logs"):
        self.run_id = run_id or str(uuid.uuid4())
        self.idea = idea
        self.log_dir = log_dir
        self.events: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.total_cost = 0.0
        
        # Ensure log directory exists
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def calculate_usage_cost(self, usage: Dict[str, Any], model: str = DEFAULT_MODEL) -> float:
        """Calculates cost in USD based on token usage."""
        if not usage or model not in MODEL_PRICING:
            return 0.0
        
        pricing = MODEL_PRICING[model]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Prices are per 1M tokens
        cost = (prompt_tokens / 1_000_000) * pricing["input"]
        cost += (completion_tokens / 1_000_000) * pricing["output"]
        return cost

    def log_event(
        self,
        agent_type: str,
        event_type: str,
        data: Dict[str, Any],
        step: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
        model: str = DEFAULT_MODEL
    ):
        """
        Logs a single event (e.g., prompt, response, tool call, usage) and calculates cost.
        """
        cost = self.calculate_usage_cost(usage, model)
        self.total_cost += cost

        event = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "event_type": event_type,
            "step": step,
            "data": data,
            "usage": usage,
            "model": model,
            "cost_usd": cost
        }
        self.events.append(event)
        
        # Print a concise trace to the console for monitoring
        tokens = f" ({usage.get('total_tokens')} tokens)" if usage else ""
        cost_str = f" [Cost: ${cost:,.6f}]" if cost > 0 else ""
        status_msg = f"[{agent_type}] {event_type}{tokens}{cost_str}"
        if step:
            status_msg += f" ({step})"
        print(f"TELEMETRY: {status_msg}")

    def save_run_log(self, final_context: Optional[Dict[str, Any]] = None):
        """
        Persists the entire run's log to a JSON file.
        """
        log_data = {
            "run_id": self.run_id,
            "idea": self.idea,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_events": len(self.events),
            "total_cost_usd": f"${self.total_cost:,.6f}",
            "events": self.events,
            "final_context": final_context,
            "final_context_summary": self._summarize_context(final_context) if final_context else None
        }
        
        file_path = os.path.join(self.log_dir, f"{self.run_id}.json")
        with open(file_path, "w") as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"TELEMETRY: Run log saved to {file_path}")

    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reduces the context to a summary for the final log (ovoiding giant data dumps).
        """
        summary = {}
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                summary[key] = f"<{len(value)} items/keys>"
            else:
                summary[key] = str(value)[:100]
        return summary


# Global telemetry instance (can be accessed by agents if they have the run_id)
_telemetry_instances: Dict[str, TelemetryManager] = {}

def get_telemetry(run_id: str, idea: str = "Unknown") -> TelemetryManager:
    if run_id not in _telemetry_instances:
        _telemetry_instances[run_id] = TelemetryManager(run_id=run_id, idea=idea)
    return _telemetry_instances[run_id]
