from .dag import DAG
from .task import Task



AGENT_REGISTRY = {

    "market_agent": market_agent,
    "tech_agent": tech_agent,
    "finance_agent": finance_agent,
    "pitch_agent": pitch_agent
}

async def build_dag(plan: Plan) -> DAG:

    dag = DAG()

    for task_plan in plan.tasks:

        agent_func = AGENT_REGISTRY.get(task_plan.agent_type)
        

        dag.add_task(

            Task(
                task_id = task_id,
                func = agent_func,
                dependencies = task_plan.dependencies
            )
        )
    return dag