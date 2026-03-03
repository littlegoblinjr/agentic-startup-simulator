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

            visited.add(task_id)

            task = self.tasks[task_id]
            
            for dependency in task.dependency:

                visit(dependency)

            stack.append(task_id)

        for task_id in self.tasks:
            visit(task_id)

        return stack
        