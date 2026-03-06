from .base import BaseTool
from .registry import register_tool

class WebSearchTool(BaseTool):


    name = "web_search"
    description = "Search the web for information"

    async def execute(self, query: str):

        return f"Results for {query}: "


register_tool(WebSearchTool())


