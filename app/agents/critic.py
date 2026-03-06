from pydantic import BaseModel
from typing import List
from openai import AsyncOpenAI
from .planner import Plan

client = AsyncOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed"
)
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

async def review_plan(startup_idea: str, plan: Plan) -> CriticResponse:

    response = await client.beta.chat.completions.parse(

        model = "liquid/lfm2.5-1.2b",
        messages = [

            {"role": "system", "content": CRITIC_PROMPT},
            {"role":"user", "content": startup_idea}
        ],
        response_format = CriticResponse
    )

    return response.choices[0].message.parsed