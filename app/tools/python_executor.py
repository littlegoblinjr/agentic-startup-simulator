from .base import BaseTool
from .registry import register_tool



class PythonExecutorTool(BaseTool):

    name = "python_execute"

    description = "Execute python code"

    async def execute(self, code: str):

        #simple safety filter
        allowed_imports = ["math"]

        if "import" in code:
            if not any(lib in code for lib in allowed_imports):
                return {"error": "Import not allowed"}

        local_vars = {}

        try:
            exec(code, {"__builtins__": {}}, local_vars)
            return {"result": local_vars}

        except Exception as e:
            return {"error": str(e)}

        


register_tool(PythonExecutorTool())