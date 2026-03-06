from .base import BaseTool
from .registry import register_tool



class PythonExecutorTool(BaseTool):

    name = "python_execute"

    description = "Execute python code"

    async def execute(self, code, str):

        local_vars = {}

        exec(code, {}, local_vars)

        return local_vars