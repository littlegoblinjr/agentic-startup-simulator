import json
from enum import Enum
from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import List, Optional, Dict, Any


from app.core.llm_config import client, DEFAULT_MODEL
class AgentType(str, Enum):
    market_agent = "market_agent"
    tech_agent = "tech_agent"
    finance_agent = "finance_agent"
    synthesis_agent = "synthesis_agent"
    pitch_agent = "pitch_agent"
    evaluation_agent = "evaluation_agent"


class TaskPlan(BaseModel):
    task_id: str
    agent_type: AgentType
    dependencies: List[str] = []
    instructions: str = "" # Specific directive for the agent in this run
    
class Plan(BaseModel):

    tasks: List[TaskPlan]


PLANNER_PROMPT = """
You are a startup planning AI.

Given a startup idea, create a workflow plan consisting of tasks assigned to specialized agents.

Available agents:
- market_agent: analyzes the market, target customers, competitors, and market size.
- tech_agent: designs the technical architecture and product implementation.
- finance_agent: creates revenue models, pricing strategy, and financial projections.
- synthesis_agent: cross-checks consistency across market, finance, and tech outputs, identifies gaps, and produces a unified strategy.
- pitch_agent: creates the final startup pitch using insights from all other agents.
- evaluation_agent: evaluates the final pitch and research for quality, consistency, and realism.

Planning rules:
1. The market_agent must run first because market analysis informs other decisions.
2. The tech_agent depends on the market_agent.
3. The finance_agent depends on the market_agent.
4. The synthesis_agent depends on market_agent, tech_agent, and finance_agent.
5. The pitch_agent depends on synthesis_agent.
6. The evaluation_agent depends on pitch_agent.
7. Ensure the workflow is a valid DAG (no cycles).
8. Use task IDs like TASK_1, TASK_2, etc.
9. Each task must include instructions that clearly state what the agent should do.

Refinement Mode:
If 'Previous Run Results' and 'User Feedback' are provided, you are in REFINEMENT MODE.
- Your goal is to PIVOT or REFINE the existing startup plan based on user feedback.
- If an agent doesn't need to change its output, you can still include it in the plan to maintain continuity.
- Use the 'instructions' field to give specific, surgical orders for the PIVOT (e.g., "Update tech stack for B2B instead of B2C").
- Reference previous findings in your instructions.
"""

from app.core.telemetry import get_telemetry

async def create_plan(
    startup_idea: str, 
    run_id: str = None, 
    parent_results: Optional[Dict[str, Any]] = None,
    feedback: Optional[str] = None
) -> Plan:
    telemetry = get_telemetry(run_id, idea=startup_idea) if run_id else None
    
    if telemetry:
        telemetry.log_event("planner", "generate_plan_start", {"idea": startup_idea})

    user_content = f"Startup Idea: {startup_idea}"
    if feedback and parent_results:
        user_content = f"""
        REFINEMENT REQUEST
        Original Idea: {startup_idea}
        User Feedback: {feedback}
        
        Previous Simulation Results Summary:
        {json.dumps(parent_results, indent=2)}
        
        Please provide an updated workflow and specific surgical instructions for the agents to implement this pivot.
        """

    response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role":"user", "content": user_content}
        ],
        response_format = Plan
    )
    
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    if telemetry:
        telemetry.log_event("planner", "generate_plan_success", {"plan": response.choices[0].message.parsed.dict()}, usage=usage)

    return response.choices[0].message.parsed

    



