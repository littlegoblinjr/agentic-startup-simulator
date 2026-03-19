from .dag import DAG
from .task import Task
from app.agents.market import market_agent
from app.agents.tech import tech_agent
from app.agents.finance import finance_agent
from app.agents.pitch import pitch_agent
from app.agents.synthesis import synthesis_agent
from app.agents.evaluation import evaluation_agent
from app.agents.planner import Plan


AGENT_REGISTRY = {

    "market_agent": market_agent,
    "tech_agent": tech_agent,
    "finance_agent": finance_agent,
    "pitch_agent": pitch_agent,
    "synthesis_agent": synthesis_agent,
    "evaluation_agent": evaluation_agent,
}

async def build_dag(plan: Plan) -> DAG:

    dag = DAG()

    for task_plan in plan.tasks:

        agent_func = AGENT_REGISTRY.get(task_plan.agent_type)
        

        dag.add_task(

            Task(
                task_id = task_plan.task_id,
                func = agent_func,
                dependencies = task_plan.dependencies
            )
        )
    return dag