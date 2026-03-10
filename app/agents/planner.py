from enum import Enum
from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import List


client = AsyncOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed"
)
class AgentType(str, Enum):
    market_agent = "market_agent"
    tech_agent = "tech_agent"
    finance_agent = "finance_agent"
    pitch_agent = "pitch_agent"


class TaskPlan(BaseModel):
    task_id: str
    agent_type: AgentType
    dependencies: List[str] = []
    
class Plan(BaseModel):

    tasks: List[TaskPlan]


PLANNER_PROMPT = """
You are a startup planning AI.

Given a startup idea, create a workflow plan consisting of tasks assigned to specialized agents.

Available agents:
- market_agent: analyzes the market, target customers, competitors, and market size.
- tech_agent: designs the technical architecture and product implementation.
- finance_agent: creates revenue models, pricing strategy, and financial projections.
- pitch_agent: creates the final startup pitch using insights from other agents.

Planning rules:
1. The market_agent must run first because market analysis informs other decisions.
2. The tech_agent depends on the market_agent.
3. The finance_agent depends on the market_agent.
4. The pitch_agent depends on market_agent, tech_agent, and finance_agent.
5. Ensure the workflow is a valid DAG (no cycles).
6. Use task IDs like TASK_1, TASK_2, etc.
7. Each task must include:
   - task_id
   - agent_type
   - dependencies (list of task_ids)

The plan should allow parallel execution where possible.
"""

async def create_plan(startup_idea:str) -> Plan:


    response = await client.beta.chat.completions.parse(

        #model = "liquid/lfm2.5-1.2b",
        model = "qwen/qwen3-4b-thinking-2507",
        messages = [

            {"role": "system", "content": PLANNER_PROMPT},
            {"role":"user", "content": startup_idea}
        ],
        response_format = Plan
    )

    return response.choices[0].message.parsed

    



