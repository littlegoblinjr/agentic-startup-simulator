from pydantic import BaseModel
from typing import List
from openai import AsyncOpenAI
from .planner import Plan
from app.core.telemetry import get_telemetry
from app.core.llm_config import client, DEFAULT_MODEL

class CriticResponse(BaseModel):
    valid: bool
    issues: str
    suggested_fix:  str | None

CRITIC_PROMPT = """
You are a workflow validation AI.

Your job is to review a startup planning workflow.

Available agents:
- market_agent
- tech_agent
- finance_agent
- pitch_agent

Expected workflow rules:
1. market_agent should run first.
2. tech_agent must depend on market_agent.
3. finance_agent must depend on market_agent.
4. pitch_agent must depend on market_agent, tech_agent, and finance_agent.
5. The workflow must form a valid DAG (no circular dependencies).
6. Only the listed agents are allowed.

Validation checklist:
- circular dependencies
- missing dependencies
- incorrect ordering
- invalid agent types
- missing required tasks

If the plan is correct, return:
valid = True

If there are issues:
valid = False
issues = explanation
suggested_fix = how the plan should be corrected.
"""

async def review_plan(startup_idea: str, plan: Plan, run_id: str = None) -> CriticResponse:
    telemetry = get_telemetry(run_id, idea=startup_idea) if run_id else None
    
    if telemetry:
        telemetry.log_event("critic", "review_plan_start", {"idea": startup_idea})

    response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages = [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role":"user", "content": startup_idea}
        ],
        response_format = CriticResponse
    )
    
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    if telemetry:
        # Pydantic v2 model_dump(), v1 dict()
        result_data = response.choices[0].message.parsed
        telemetry.log_event("critic", "review_plan_success", {"result": result_data.model_dump() if hasattr(result_data, 'model_dump') else result_data.dict()}, usage=usage)

    return response.choices[0].message.parsed