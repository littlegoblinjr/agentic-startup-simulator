"""
Structured Trace Exporter.

Reconstructs per-agent reasoning traces from TelemetryManager events and
exports them in JSONL format — one line per agent call — ready for use in
SFT (supervised fine-tuning) or RLHF pipelines.

Each trace record captures:
  - run metadata (run_id, idea, timestamp)
  - agent identity
  - reconstructed message thread (system prompt → user input → response)
  - parsed output (the structured dict written to context)
  - quality gate result (structural validation)
  - token usage and cost
  - human label slot (null until human feedback is provided)

Usage:
    from app.evaluation.trace_exporter import TraceExporter
    exporter = TraceExporter(run_id, context, telemetry)
    jsonl_str = exporter.export_jsonl()          # full multi-agent trace
    records   = exporter.build_trace_records()   # as list of dicts
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.telemetry import TelemetryManager, get_telemetry


# ── Agent output keys in context ──────────────────────────────────────────────
_AGENT_CONTEXT_KEY: Dict[str, str] = {
    "market_agent":     "market_analysis",
    "tech_agent":       "tech_analysis",
    "finance_agent":    "financial_projections",
    "synthesis_agent":  "synthesis",
    "pitch_agent":      "pitch_deck",
    "evaluation_agent": "evaluation_scorecard",
}

# Event types that carry the final agent output in `data`
_FINAL_EVENT_TYPES = {
    "market_agent":     {"success", "final_forcing_success"},
    "tech_agent":       {"success", "final_forcing_success"},
    "finance_agent":    {"success", "final_forcing_success"},
    "synthesis_agent":  {"round_2_success", "fallback_success"},
    "pitch_agent":      {"final_pitch"},
    "evaluation_agent": {"final_scorecard"},
}

# Event types that hold prompt/input content
_INPUT_EVENT_TYPES = {"start", "generate_queries", "review_plan_start"}


class TraceExporter:
    """
    Builds JSONL trace records for a completed simulation run.

    Parameters
    ----------
    run_id : str
        Unique identifier of the simulation run.
    context : dict
        The final shared context dict produced by the scheduler.
    telemetry : TelemetryManager, optional
        If not supplied, looked up from the global registry by run_id.
    """

    def __init__(
        self,
        run_id: str,
        context: Dict[str, Any],
        telemetry: Optional[TelemetryManager] = None,
    ):
        self.run_id = run_id
        self.context = context
        self.idea = context.get("idea", "Unknown")
        self.telemetry = telemetry or get_telemetry(run_id, idea=self.idea)

    # ── Public API ────────────────────────────────────────────────────────────

    def build_trace_records(self) -> List[Dict[str, Any]]:
        """Return a list of trace dicts, one per agent that ran."""
        records = []
        for agent_type, ctx_key in _AGENT_CONTEXT_KEY.items():
            output = self.context.get(ctx_key)
            if output is None:
                continue  # agent was skipped

            agent_events = [
                e for e in self.telemetry.events
                if e.get("agent_type") == agent_type
            ]

            record = self._build_record(agent_type, ctx_key, agent_events, output)
            records.append(record)

        return records

    def export_jsonl(self) -> str:
        """
        Serialize all trace records as JSONL (one JSON object per line).
        Suitable for direct upload to SFT / RLHF pipelines.
        """
        records = self.build_trace_records()
        lines = [json.dumps(r, default=str, ensure_ascii=False) for r in records]
        return "\n".join(lines)

    def export_dict(self) -> Dict[str, Any]:
        """
        Return a run-level export object (useful for the REST API response).
        Contains metadata + all per-agent trace records.
        """
        quality_flags = self.context.get("quality_flags", {})
        scorecard     = self.context.get("evaluation_scorecard", {})

        return {
            "run_id":          self.run_id,
            "idea":            self.idea,
            "export_format":   "sft_trace_v1",
            "exported_at":     datetime.utcnow().isoformat() + "Z",
            "total_cost_usd":  self.telemetry.total_cost,
            "evaluation_score": (
                scorecard.get("total_score") if isinstance(scorecard, dict) else None
            ),
            "quality_summary": {
                "agents_passed": quality_flags.get("agents_passed"),
                "agents_failed": quality_flags.get("agents_failed"),
                "total_issues":  quality_flags.get("total_issues"),
            },
            "traces": self.build_trace_records(),
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _build_record(
        self,
        agent_type: str,
        ctx_key: str,
        events: List[Dict[str, Any]],
        output: Any,
    ) -> Dict[str, Any]:
        """Construct a single per-agent trace record."""

        # -- Reconstruct message thread from telemetry events --
        messages = self._reconstruct_messages(agent_type, events)

        # -- Aggregate token usage across all events for this agent --
        total_usage = self._aggregate_usage(events)

        # -- Pull quality gate result for this agent --
        quality_flags = self.context.get("quality_flags", {})
        per_agent     = quality_flags.get("per_agent", {})
        gate_result   = per_agent.get(ctx_key.replace("_analysis", "_agent")
                                               .replace("financial_projections", "finance_agent")
                                               .replace("pitch_deck", "pitch_agent")
                                               .replace("evaluation_scorecard", "evaluation_agent")
                                               .replace("synthesis", "synthesis_agent"), None)

        # -- Find the timestamp of the agent's start event --
        start_event = next(
            (e for e in events if e.get("event_type") in {"start", "evaluation_start", "generate_pitch_start"}),
            events[0] if events else {},
        )

        return {
            # ── Metadata ───────────────────────────────────────────────────────
            "run_id":      self.run_id,
            "idea":        self.idea,
            "agent":       agent_type,
            "context_key": ctx_key,
            "timestamp":   start_event.get("timestamp", datetime.utcnow().isoformat()),

            # ── Trace (SFT-ready format) ───────────────────────────────────────
            "messages": messages,

            # ── Ground truth output ────────────────────────────────────────────
            "response": output,

            # ── Quality signal ─────────────────────────────────────────────────
            "quality_gate": gate_result,

            # ── Token / cost telemetry ─────────────────────────────────────────
            "token_usage": total_usage,

            # ── Human feedback slot (filled by POST /run/{run_id}/feedback) ────
            "human_label":   None,
            "human_rating":  None,
            "human_comment": None,
        }

    def _reconstruct_messages(
        self, agent_type: str, events: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Reconstruct a representative messages list (system + user + assistant)
        from telemetry events.  We use the idea as the user turn and the
        parsed output as the assistant turn.  For agents with an agentic loop
        (market / tech / finance) we include intermediate tool-call summaries.
        """
        messages: List[Dict[str, str]] = []

        # System: use the agent's start data or a generic label
        start_ev = next(
            (e for e in events if e.get("event_type") in {"start", "evaluation_start", "generate_pitch_start", "review_plan_start"}),
            None,
        )
        system_note = f"[{agent_type}] — reconstructed from telemetry"
        if start_ev:
            data = start_ev.get("data", {})
            system_note = data.get("idea") or data.get("input_summary") or system_note

        messages.append({"role": "system", "content": f"Agent: {agent_type}"})
        messages.append({"role": "user",   "content": f"Startup Idea: {self.idea}"})

        # Tool calls (web search queries) — enrich trace for agents that loop
        tool_events = [e for e in events if e.get("event_type") == "tool_call"]
        if tool_events:
            queries = [
                e.get("data", {}).get("query", "")
                for e in tool_events
                if e.get("data", {}).get("tool") == "web_search"
            ]
            if queries:
                messages.append({
                    "role": "assistant",
                    "content": f"[tool_calls: web_search] Queries: {queries}",
                })

        # Refinement rounds if any
        refine_events = [
            e for e in events
            if e.get("event_type") in {"refine_finance_start", "refine_tech_start", "round_2_start"}
        ]
        if refine_events:
            messages.append({
                "role": "assistant",
                "content": f"[refinement] {len(refine_events)} refinement round(s) triggered",
            })

        return messages

    @staticmethod
    def _aggregate_usage(events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Sum prompt/completion/total tokens across all events for an agent."""
        prompt     = 0
        completion = 0
        total      = 0
        for e in events:
            usage = e.get("usage") or {}
            prompt     += usage.get("prompt_tokens",     0)
            completion += usage.get("completion_tokens", 0)
            total      += usage.get("total_tokens",      0)
        return {
            "prompt_tokens":     prompt,
            "completion_tokens": completion,
            "total_tokens":      total,
        }
