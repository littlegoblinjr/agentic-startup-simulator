import asyncio
from app.memory.db import init_db
from app.agents.planner import create_plan
from app.memory.vector_store import retrieve_memory, store_memory
from app.orchestrator.dag_builder import build_dag
from app.orchestrator.scheduler import Scheduler
from app.tools.web_search import WebSearchTool
from app.tools.registry import register_tool
from app.tools.python_executor import PythonExecutorTool

async def test_pipeline():

    idea = "A platform that connects local farmers directly with consumers, cutting out the middleman and providing fresher produce at lower prices."
    
    
    await init_db()
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
    
    
    
    
    await store_memory(
        
        content = str(context.get("market_analysis")),
        metadata={
            "type": "market_analysis",
            "idea": idea,
        }
    )
    
    await store_memory(
        content = str(context.get("technical_architecture")),
        metadata={
            "type": "technical_architecture",
            "idea": idea,
        }
    )
    
    await store_memory(
        content = str(context.get("financial_plan")),
        metadata={
            "type": "financial_plan",
            "idea": idea,
        }
    )
    
    await store_memory(
        content = str(context.get("pitch")),
        metadata={
            "type": "pitch",
            "idea": idea,
        }
    )   

    print("FINAL CONTEXT: \n ")


    print(context)

if __name__ == "__main__":
    asyncio.run(test_pipeline())










