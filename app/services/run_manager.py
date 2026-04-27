import uuid
import asyncio
from typing import Dict, Any, Optional

from app.agents.planner import create_plan
from app.agents.critic import review_plan
from app.orchestrator.dag_builder import build_dag
from app.orchestrator.scheduler import Scheduler
from app.core.telemetry import get_telemetry
from app.evaluation.quality_gates import run_all_quality_gates


class RunManager:
    """
    Orchestrates a complete simulation run:
    1. Plan & Review Loop
    2. DAG Generation
    3. Execution via Scheduler
    4. Telemetry Management
    """

    @staticmethod
    async def run_simulation(
        idea: str, 
        run_id: Optional[str] = None, 
        parent_results: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        run_id = run_id or str(uuid.uuid4())
        print(f"RUN_MANAGER: Starting simulation for idea: '{idea}' (Run ID: {run_id})")
        
        # 1. Planning Phase (Direct execution to avoid Critic loops)
        plan = await create_plan(idea, run_id=run_id, parent_results=parent_results, feedback=feedback)

        # 2. DAG Preparation
        dag = await build_dag(plan)
        context = {
            "idea": idea,
            "run_id": run_id,
            "skipped_agents": [a.value for a in plan.skipped_agents] if hasattr(plan, "skipped_agents") else [],
            **(parent_results or {})
        }

        # 3. Execution Phase
        scheduler = Scheduler(dag, context)
        print("RUN_MANAGER: Executing task DAG...")
        await scheduler.execute()

        # 4. Per-agent quality gates — run after all agents complete
        telemetry = get_telemetry(run_id, idea=idea)
        quality_summary = run_all_quality_gates(context)
        print(
            f"RUN_MANAGER: Quality gates — "
            f"{quality_summary['agents_passed']}/{quality_summary['agents_validated']} passed, "
            f"{quality_summary['total_issues']} issue(s) found"
        )
        telemetry.log_event(
            "quality_gates",
            "validation_complete",
            {
                "agents_passed":    quality_summary["agents_passed"],
                "agents_failed":    quality_summary["agents_failed"],
                "total_issues":     quality_summary["total_issues"],
                "overall_passed":   quality_summary["overall_passed"],
            },
        )
        
        # 5. Results — safe score extraction
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
            "final_context": context,
            "log_path": f"logs/{run_id}.json"
        }


if __name__ == "__main__":
    # Test run
    test_idea = "A mobile app for tracking personal carbon footprints using AI receipts scanning"
    asyncio.run(RunManager.run_simulation(test_idea))
