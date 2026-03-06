from typing import Dict
from .base import BaseTool


TOOL_REGISTRY: Dict[str, BaseTool] = {}

def register_tool(tool: BaseTool):
    TOOL_REGISTRY[tool.name] = tool

def get_tool(name: str) -> BaseTool:

    if name not in BaseTool:
        raise ValueError(f"Tool {name} not found")

    return TOOL_REGISTRY[name]

