import asyncio
import uuid
from .state import TaskState
from app.core.telemetry import TelemetryManager, get_telemetry


class Scheduler:

    def __init__(self, dag, context):
        self.dag = dag
        self.context = context

    async def execute(self):
        # Ensure context has a run_id for telemetry
        if "run_id" not in self.context:
            self.context["run_id"] = str(uuid.uuid4())
            
        telemetry = get_telemetry(self.context["run_id"], idea=self.context.get("idea", "Unknown"))
        
        tasks_map = self.dag.tasks

        while True:

            pending_tasks = [t for t in tasks_map.values() if t.state == TaskState.PENDING]

            if not pending_tasks:
                break

            runnable = []
            for t in pending_tasks:

                if all(tasks_map[dep].state == TaskState.COMPLETED for dep in t.dependencies):
                    runnable.append(t)

                elif any(tasks_map[dep].state == TaskState.FAILED for dep in t.dependencies):
                    t.state = TaskState.FAILED
                    t.error = "Dependency failed"

            # Deadlock guard: no tasks can make progress, exit to avoid infinite spin
            if not runnable:
                print("SCHEDULER: no runnable tasks, breaking to avoid deadlock.")
                break

            await asyncio.gather(*[t.run(self.context) for t in runnable])

        # Save the final log
        telemetry.save_run_log(final_context=self.context)
