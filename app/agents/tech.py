from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import List
from app.tools.schemas import ToolCall
from app.tools.executor import execute_tool
import json


client = AsyncOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed"
)


TECH_PROMPT = """
You are a technical architect agent.

Your job is to analyze a startup and produce a structured technical architecture.

You may use the available tools if you need external information.

Available tools:

web_search
Description: Search the internet for information about technologies, frameworks, and tools.

Tool call format (JSON only):

{
  "tool_name": "web_search",
  "arguments": {
    "query": "search query"
  }
}

If multiple searches are needed, return them as a list:

{
  "tool_calls": [
    {
      "tool_name": "web_search",
      "arguments": {"query": "..."}
    },
    {
      "tool_name": "web_search",
      "arguments": {"query": "..."}
    }
  ]
}

Decision rule:

If the startup idea requires information about technologies, frameworks, or tools,
you MUST call the web_search tool first before producing the final answer.

When you have enough information, return the final technical architecture in JSON using this schema:

{
  "architecture": "description",
  "tech_stack": ["tech1", "tech2"],
  "database": "description",
  "deployment": "description",
  "scalability": "description",
  "security": "description"
}

Rules:

- Always return valid JSON
- Return ONLY JSON
- Either return a tool call OR the final architecture JSON
"""


async def tech_agent(context):

    market_analysis = context["market_analysis"]

    messages = [
        {"role": "system", "content": TECH_PROMPT},
        {"role": "user", "content": json.dumps(market_analysis)}
    ]

    for _ in range(5):

        response = await client.chat.completions.create(
            #model="liquid/lfm2.5-1.2b",
            model = "qwen2.5-3b-instruct",
            messages=messages
        )

        output = response.choices[0].message.content

        try:

            data = json.loads(output)

            if "tool_calls" in data:

                results = []

                for call in data["tool_calls"]:

                    tool_call = ToolCall(**call)
                    print(  "Calling tool for tech: ", tool_call.tool_name)
                    result = await execute_tool(
                        tool_call.tool_name,
                        tool_call.arguments
                    )
                    print("Tool result: ", result)

                    results.append(result)

                messages.append({
                    "role": "assistant",
                    "content": output
                })

                messages.append({
                    "role": "tool",
                    "content": json.dumps(results)
                })

                continue

            context["tech_architecture"] = data
            return data

        except Exception as e:
            print("TECH AGENT ERROR:", e)
            raise


    
