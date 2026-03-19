import uuid
import asyncio
from typing import Dict, Any, Optional

from app.agents.planner import create_plan
from app.agents.critic import review_plan
from app.orchestrator.dag_builder import build_dag
from app.orchestrator.scheduler import Scheduler
from app.core.telemetry import get_telemetry


class RunManager:
    """
    Orchestrates a complete simulation run:
    1. Plan & Review Loop
    2. DAG Generation
    3. Execution via Scheduler
    4. Telemetry Management
    """

    @staticmethod
    async def run_simulation(idea: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        run_id = run_id or str(uuid.uuid4())
        print(f"RUN_MANAGER: Starting simulation for idea: '{idea}' (Run ID: {run_id})")
        
        # 1. Planning Phase
        plan = await create_plan(idea, run_id=run_id)
        review = await review_plan(idea, plan, run_id=run_id)
        
        if not review.valid:
            print(f"RUN_MANAGER: Initial plan invalid, refining... Issues: {review.issues}")
            plan = await create_plan(f"Fix this plan based on issues: {review.issues}. Suggested fix: {review.suggested_fix}. Original plan: {plan}", run_id=run_id)

        # 2. DAG Preparation
        dag = await build_dag(plan)
        context = {
            "idea": idea,
            "run_id": run_id
        }

        # 3. Execution Phase
        scheduler = Scheduler(dag, context)
        print("RUN_MANAGER: Executing task DAG...")
        await scheduler.execute()
        
        # 4. Results
        telemetry = get_telemetry(run_id, idea=idea)
        
        # Safe score extraction
        scorecard = context.get('evaluation_scorecard', {})
        score = "N/A"
        if hasattr(scorecard, "total_score"):
            score = scorecard.total_score
        elif isinstance(scorecard, dict):
            score = scorecard.get("total_score", "N/A")
            
        print(f"RUN_MANAGER: Simulation complete. Evaluation score: {score}")
        
        return {
            "run_id": run_id,
            "idea": idea,
            "plan": plan.dict() if hasattr(plan, 'dict') else plan,
            "results": context,
            "log_path": f"logs/{run_id}.json"
        }


if __name__ == "__main__":
    # Test run
    test_idea = "A mobile app for tracking personal carbon footprints using AI receipts scanning"
    asyncio.run(RunManager.run_simulation(test_idea))
