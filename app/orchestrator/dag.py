from typing import Dict
from .task import Task


class DAG:

    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task):
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Task:
        return self.tasks[task_id]


    def topological_sort(self):

        visited = set()
        stack = []
        def visit(task_id):
            if task_id in visited:
                return

            # Safety: In refinement mode, the planner might hallucinate virtual task IDs (like REFINEMENT_REQUEST).
            # We ignore any dependencies that are not in the current plan's task list.
            if task_id not in self.tasks:
                print(f"DAG WARNING: Ignoring virtual or missing dependency '{task_id}'")
                return

            visited.add(task_id)
            task = self.tasks[task_id]
            
            for dependency in task.dependencies:
                visit(dependency)

            stack.append(task_id)

        for task_id in self.tasks:
            visit(task_id)

        return stack
        