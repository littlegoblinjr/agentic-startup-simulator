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
You are a workflow validation AI. Your job is to review a startup planning workflow.

Refinement Mode Awareness:
The simulation can run in "Initial" or "Refinement" mode. 
In Refinement Mode, the plan may be PARTIAL (surgical). For example, if the user only wants more depth in finance, the plan might ONLY contain finance_agent and its downstream dependencies.

Available agents:
- market_agent
- tech_agent
- finance_agent
- synthesis_agent
- pitch_agent
- evaluation_agent

Expected workflow rules (General):
1. market_agent usually runs first.
2. tech_agent must depend on market_agent.
3. finance_agent must depend on market_agent.
4. synthesis_agent depends on market, tech, and finance.
5. pitch_agent depends on synthesis_agent.
6. evaluation_agent depends on pitch_agent.

Surgical Validation Rules:
- If a required dependency (e.g., market_agent) is MISSING from the current plan, but its results would already be in the 'context' from a previous run, the plan is VALID.
- Task IDs: The plan uses task_id (e.g., TASK_1, TASK_2) for dependencies. DO NOT expect the agent_type string in the dependencies list.
- To validate a dependency, find the task with that task_id and check its agent_type.
- Example: If tech_agent depends on TASK_1, and TASK_1 is market_agent, that is a VALID dependency.
- Ensure only the necessary agents are being triggered to save tokens.
- The workflow must still form a valid DAG (no circular dependencies).
- CRITICAL: Every task_id in the dependencies list MUST exist as a task in the current plan. DO NOT ALLOW virtual IDs like 'REFINEMENT_REQUEST'.

Validation checklist:
1. Circular dependencies (Check task_id edges for cycles).
2. Dependency on a task_id that does not exist in the current plan AND its required agent_type is missing from previous results (Invalid).
3. Invalid agent types (Invalid).

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
            {"role":"user", "content": f"Startup Idea: {startup_idea}\n\nProposed Plan:\n{plan.model_dump_json(indent=2) if hasattr(plan, 'model_dump_json') else json.dumps(plan.dict(), indent=2)}"}
        ],
        response_format = CriticResponse
    )
    
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    if telemetry:
        # Pydantic v2 model_dump(), v1 dict()
        result_data = response.choices[0].message.parsed
        telemetry.log_event("critic", "review_plan_success", {"result": result_data.model_dump() if hasattr(result_data, 'model_dump') else result_data.dict()}, usage=usage)

    return response.choices[0].message.parsed