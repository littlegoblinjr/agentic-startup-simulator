import asyncio

from app.agents.planner import create_plan

from app.orchestrator.dag_builder import build_dag
from app.orchestrator.scheduler import Scheduler
from app.tools.web_search import WebSearchTool
from app.tools.registry import register_tool
from app.tools.python_executor import PythonExecutorTool

async def test_pipeline():

    idea = "Ai therapy companion for college students"

    register_tool(WebSearchTool())
    register_tool(PythonExecutorTool())
    plan = await create_plan(idea)

    print("Plan\n")
    print(plan)
    

    dag = await build_dag(plan) 

    context = {

        "idea": idea
    }

    scheduler = Scheduler(dag, context)

    await scheduler.execute()

    print("FINAL CONTEXT: \n ")


    print(context)

if __name__ == "__main__":
    asyncio.run(test_pipeline())










