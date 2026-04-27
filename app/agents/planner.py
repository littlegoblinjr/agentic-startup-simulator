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
    is_partial_refinement: bool
    tasks: List[TaskPlan]
    skipped_agents: List[AgentType] = []
    reasoning: str # Why this specific set of agents was chosen


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

General Task Rules:
1. Ensure the workflow is a valid DAG (no cycles).
2. Use task IDs like TASK_1, TASK_2, etc.
3. Each task must include instructions that clearly state what the agent should do.

Standard Architecture Dependencies:
- `market_agent` has no dependencies.
- `tech_agent` depends on `market_agent`.
- `finance_agent` depends on `market_agent`.
- `synthesis_agent` depends on `market_agent`, `tech_agent`, and `finance_agent`.
- `pitch_agent` depends on `synthesis_agent`.
- `evaluation_agent` depends on `pitch_agent`.

CRITICAL DAG RULE FOR REFINEMENTS:
If an upstream agent (like `market_agent` or `tech_agent`) is SKIPPED, downstream agents MUST STILL list them in their `dependencies` array if they need their data. Do NOT include an upstream agent in the `tasks` list just to satisfy a dependency. The system automatically injects skipped data.
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
        
        Previous Simulation Results Summary (JSON):
        {json.dumps(parent_results, indent=2, default=str)}
        
        Available Data Keys (DO NOT RERUN IF SUFFICIENT): {list(parent_results.keys())}
        
        MANDATE: Only provide an updated workflow for the SPECIFIC areas requested. If the feedback is just "more research in finance", DO NOT rerun market or tech.
        
        Refinement Rules:
        - EXCLUSION MANDATE: If an agent's previous output is sufficient, you MUST EXCLUDE it from the `tasks` list. 
        - WARNING: If you include a task in the list, THE SYSTEM WILL EXECUTE IT. Do not include a task just to say "no changes needed."
        1. You may skip any agent whose output does not need to change.
        2. If you skip an agent, add its AgentType to `skipped_agents`.
        3. ONLY include downstream agents (e.g. synthesis/pitch) if the upstream changes are significant enough to require a strategy/pitch rewrite.
        4. set `is_partial_refinement = true`.
        5. DOMAIN MAPPING: Carefully analyze the user's feedback. If they ONLY ask for financial changes (e.g., pricing, revenue, costs), you MUST skip `market_agent` and `tech_agent`. If they ask for tech changes (e.g., stack, architecture), skip `market_agent` and `finance_agent`. If they explicitly ask for a full rewrite, you may include all agents.
        """
    else:
        user_content = f"""
        INITIAL LAUNCH REQUEST
        Startup Idea: {startup_idea}
        
        Initial Launch Rules:
        1. MANDATE: This is a completely new idea. You MUST include ALL 6 agents in the `tasks` list. `skipped_agents` MUST be an empty list [].
        2. Follow the Standard Architecture Dependencies exactly.
        3. set `is_partial_refinement = false`.
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

    



