from openai import AsyncOpenAI
from pydantic import BaseModel
from app.tools.schemas import ToolCall
from typing import List
from app.tools.executor import execute_tool

import json

client = AsyncOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed"
)

MARKET_PROMPT = """

You are a market research agent.

Your job is to analyze a startup idea and produce a structured market analysis.

You may use the available tools if you need external information.

Available tools:

web_search
Description: Search the internet for information about markets, companies, competitors, and trends.

Tool call format (JSON only):

{
  "tool_name": "web_search",
  "arguments": {
    "query": "search query"
  }
}

Decision rule:

If the startup idea requires information about competitors, market size, or trends,
you MUST call the web_search tool first before producing the final answer.

When you have enough information, return the final analysis in JSON using this schema:

{
  "target_audience": "description",
  "market_size": "description",
  "competitors": ["company1", "company2"],
  "market_trends": ["trend1", "trend2"],
  "opportunities": ["opportunity1", "opportunity2"],
  "risks": ["risk1", "risk2"]
}

Rules:

- Always return valid JSON.
- Return ONLY JSON. Do not include any extra text.
- Either return a tool call OR the final market analysis JSON.
- Never return both.


"""

async def market_agent(context):

    idea = context["idea"]

    messages = [
        {"role": "system", "content": MARKET_PROMPT},
        {"role": "user", "content": idea}
    ]
    for _ in range(5):

        response = await client.chat.completions.create(
            model = "liquid/lfm2.5-1.2b",
            messages = messages
        )

        output = response.choices[0].message.content

        try:

            tool_call = ToolCall.model_validate_json(output)
            result = await execute_tool(

                tool_call.tool_name,
                tool_call.arguments
            )

            messages.append({"role": "assistant", "content": output})
            messages.append({"role": "user", "content": json.dumps(result)})

        except Exception:
            context["market_analysis"] = output
            return output


    

    

        