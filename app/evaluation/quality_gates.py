"""
Per-agent quality gates.

Each gate validates the structured output of one agent against a set of
data-driven rules (completeness, minimum content, list depth). Results are
aggregated into a `quality_flags` dict stored on the shared context.

This runs *after* each agent writes its result into context but *before* the
evaluation_agent produces a final score, giving the score grounded signal
rather than relying solely on LLM self-assessment.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

# ── Sentinel values that indicate a missing / placeholder answer ──────────────
_PLACEHOLDER_TOKENS = {
    "n/a", "na", "tbd", "todo", "none", "null", "unknown", "placeholder",
    "description", "tech1", "tech2", "company1", "company2",
}

MIN_STRING_LENGTH = 40   # minimum meaningful text length per string field
MIN_LIST_ITEMS   = 2     # minimum items in any list field


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_hollow(value: str) -> bool:
    """Return True if a string field is empty, too short, or a placeholder."""
    if not value or not isinstance(value, str):
        return True
    stripped = value.strip()
    if len(stripped) < MIN_STRING_LENGTH:
        return True
    if stripped.lower() in _PLACEHOLDER_TOKENS:
        return True
    return False


def _check_strings(data: Dict[str, Any], fields: List[str]) -> List[str]:
    issues = []
    for field in fields:
        val = data.get(field)
        if _is_hollow(val):
            issues.append(f"'{field}' is missing or too short (got: {repr(str(val)[:60])})")
    return issues


def _check_lists(data: Dict[str, Any], fields: List[str], min_items: int = MIN_LIST_ITEMS) -> List[str]:
    issues = []
    for field in fields:
        val = data.get(field)
        if not isinstance(val, list) or len(val) < min_items:
            n = len(val) if isinstance(val, list) else 0
            issues.append(f"'{field}' needs ≥{min_items} items (got {n})")
        else:
            # Ensure individual items aren't just placeholders
            hollow = [item for item in val if _is_hollow(str(item))]
            if hollow:
                issues.append(f"'{field}' contains placeholder items: {hollow[:3]}")
    return issues


def _gate_result(agent: str, issues: List[str]) -> Dict[str, Any]:
    return {
        "agent": agent,
        "passed": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
    }


# ── Per-agent validators ──────────────────────────────────────────────────────

def validate_market_analysis(data: Any) -> Dict[str, Any]:
    """
    Expected schema:
        target_audience: str, market_size: str,
        competitors: List[str] (≥4),
        market_trends: List[str] (≥2),
        opportunities: List[str] (≥2),
        risks: List[str] (≥2)
    """
    if not isinstance(data, dict):
        return _gate_result("market_agent", ["Output is not a dict"])

    issues = []
    issues += _check_strings(data, ["target_audience", "market_size"])
    issues += _check_lists(data, ["competitors"], min_items=4)
    issues += _check_lists(data, ["market_trends", "opportunities", "risks"])
    return _gate_result("market_agent", issues)


def validate_tech_analysis(data: Any) -> Dict[str, Any]:
    """
    Expected schema:
        architecture: str, database: str, deployment: str,
        scalability: str, security: str,
        tech_stack: List[str] (≥2)
    """
    if not isinstance(data, dict):
        return _gate_result("tech_agent", ["Output is not a dict"])

    issues = []
    issues += _check_strings(data, ["architecture", "database", "deployment", "scalability", "security"])
    issues += _check_lists(data, ["tech_stack"])
    return _gate_result("tech_agent", issues)


def validate_financial_projections(data: Any) -> Dict[str, Any]:
    """
    Expected schema:
        revenue_model: str, pricing_strategy: str,
        cost_structure: str, break_even_estimate: str,
        financial_projection: str  (note: agent uses singular key)
    """
    if not isinstance(data, dict):
        return _gate_result("finance_agent", ["Output is not a dict"])

    issues = []
    # Finance agent uses both "financial_projection" and "financial_projections" (synthesis uses latter)
    finance_fields = ["revenue_model", "pricing_strategy", "cost_structure", "break_even_estimate"]
    issues += _check_strings(data, finance_fields)

    # Accept either key name for the projection field
    proj = data.get("financial_projection") or data.get("financial_projections")
    if _is_hollow(str(proj) if proj else ""):
        issues.append("'financial_projection' is missing or too short")

    return _gate_result("finance_agent", issues)


def validate_synthesis(data: Any) -> Dict[str, Any]:
    """
    Expected schema:
        refined_strategy: str,
        consistency_issues: List[str],
        gaps: List[str],
        key_risks: List[str],
        recommendations: List[str] (≥2)
    """
    if not isinstance(data, dict):
        return _gate_result("synthesis_agent", ["Output is not a dict"])

    issues = []
    issues += _check_strings(data, ["refined_strategy"])
    issues += _check_lists(data, ["consistency_issues", "gaps", "key_risks", "recommendations"])
    return _gate_result("synthesis_agent", issues)


def validate_pitch(data: Any) -> Dict[str, Any]:
    """
    Expected schema: all string fields from PitchSchema
    """
    if not isinstance(data, dict):
        return _gate_result("pitch_agent", ["Output is not a dict"])

    issues = []
    fields = [
        "startup_name", "problem", "solution_summary", "target_market",
        "competitive_edge", "business_model", "technology",
        "go_to_market", "financial_projection", "vision_statement",
    ]
    issues += _check_strings(data, fields)
    return _gate_result("pitch_agent", issues)


def validate_evaluation_scorecard(data: Any) -> Dict[str, Any]:
    """Validate the final scorecard from evaluation_agent."""
    if not isinstance(data, dict):
        return _gate_result("evaluation_agent", ["Output is not a dict"])

    issues = []
    total = data.get("total_score")
    if total is None or not isinstance(total, (int, float)):
        issues.append("'total_score' is missing or not a number")
    elif not (0 <= total <= 100):
        issues.append(f"'total_score' is out of range 0-100: {total}")

    criteria = data.get("criteria_scores", {})
    for sub in ["consistency", "completeness", "realism", "risk_mitigation"]:
        if sub not in criteria:
            issues.append(f"criteria_scores.'{sub}' is missing")

    feedback = data.get("feedback", {})
    for key in ["strengths", "weaknesses"]:
        if not isinstance(feedback.get(key), list) or len(feedback.get(key, [])) == 0:
            issues.append(f"feedback.'{key}' must be a non-empty list")

    if _is_hollow(feedback.get("investor_verdict", "")):
        issues.append("feedback.'investor_verdict' is missing or too short")

    return _gate_result("evaluation_agent", issues)


# ── Context-level orchestrator ────────────────────────────────────────────────

# Maps context key → validator function
_AGENT_VALIDATORS = {
    "market_analysis":      validate_market_analysis,
    "tech_analysis":        validate_tech_analysis,
    "financial_projections": validate_financial_projections,
    "synthesis":            validate_synthesis,
    "pitch_deck":           validate_pitch,
    "evaluation_scorecard": validate_evaluation_scorecard,
}


def run_all_quality_gates(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all quality gates against available context keys.
    Returns a summary dict stored at context["quality_flags"].

    Only validates agents whose output is actually present in context
    (skipped agents won't have output).
    """
    results: Dict[str, Dict[str, Any]] = {}

    for ctx_key, validator in _AGENT_VALIDATORS.items():
        data = context.get(ctx_key)
        if data is None:
            continue  # agent was skipped — don't penalise
        results[validator.__name__.replace("validate_", "")] = validator(data)

    passed_count  = sum(1 for r in results.values() if r["passed"])
    total_count   = len(results)
    total_issues  = sum(r["issue_count"] for r in results.values())

    summary = {
        "agents_validated": total_count,
        "agents_passed":    passed_count,
        "agents_failed":    total_count - passed_count,
        "total_issues":     total_issues,
        "overall_passed":   total_issues == 0,
        "per_agent":        results,
    }

    context["quality_flags"] = summary
    return summary
