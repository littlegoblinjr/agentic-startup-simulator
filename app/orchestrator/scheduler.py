import asyncio
from .state import TaskState


class Scheduler:

    def __init__(self, dag, context):
        self.dag = dag
        self.context = context

    async def execute(self):

        task = self.dag.tasks

        while True:

            pending_tasks = [t for t in task.values() if t.state == TaskState.PENDING]

            if not pending_tasks:
                break

            runnable = []        
            for t in pending_tasks:

                if all(task[dep].state == TaskState.COMPLETED for dep in t.dependencies):

                    runnable.append(t)

                if any(task[dep].state == TaskState.FAILED for dep in t.dependencies):

                    t.state = TaskState.FAILED
                    t.error = "Dependency failed"


            
            results = await asyncio.gather(*[t.run(self.context) for t in runnable])
                    
                    

