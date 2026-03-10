from .registry import get_tool
import asyncio


async def execute_tool(tool_name, arguments):

    tool = get_tool(tool_name)
    print("Tool retrieved:", tool)
    result = await asyncio.wait_for(
        tool.execute(**arguments),
        timeout = 30
    )

    return result