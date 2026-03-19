import asyncio
from typing import Callable, List
from .state import TaskState

class Task:

    def __init__(self, 

            task_id: str,
            func: Callable,
            dependencies: List[str] = None,
            retries: int = 1,
            ):

        self.task_id = task_id
        self.func = func
        self.dependencies = dependencies or []
        self.retries = retries
        self.state = TaskState.PENDING
        self.result = None
        self.error = None


    async def run(self, context):
        
        attempt = 0


        while attempt < self.retries:
            try:

                result = await self.func(context)
                # Auto-convert Pydantic models to dict for JSON serialization
                if hasattr(result, "dict"):
                    result = result.dict()
                elif hasattr(result, "model_dump"):
                    result = result.model_dump()
                
                self.result = result
                self.state = TaskState.COMPLETED
                return self.result
            
            except Exception as e:

                
                attempt += 1
                self.error = e

                if attempt >= self.retries:
                    self.state = TaskState.FAILED
                
                    raise e

                await asyncio.sleep(1)


        


