from openai import AsyncOpenAI
from app.tools.schemas import ToolCall
from app.tools.executor import execute_tool
from typing import List
import json
FINANCE_PROMPT = """

You are a startup finance analyst.

Your job is to analyze the startup idea and produce a structured financial plan.

You may use the available tools if additional information or calculations are needed.

Available tools:

web_search
Description: Search the internet for financial data, market benchmarks, pricing strategies, and startup funding information.

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

python_execute
Description: Execute Python code for financial calculations and projections.

Tool call format (JSON only):

{
  "tool_name": "python_execute",
  "arguments": {
    "code": "python code"
  }
}


Decision rules:

- If financial data, benchmarks, market pricing, or industry information is needed, you MAY call the web_search tool.
- If numerical calculations or projections are required, you MUST call the python_execute tool.

When you have enough information, return the final financial analysis in JSON using this schema:

{
  "revenue_model": "description",
  "pricing_strategy": "description",
  "cost_structure": "description",
  "break_even_estimate": "description",
  "financial_projection": "description"
}

Rules:

- Always return valid JSON
- Return ONLY JSON
- Either return tool calls OR the final financial JSON
- Never return both


"""


client = AsyncOpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="not-needed"
)


async def finance_agent(context):

    market_analysis = context["market_analysis"]
    

    messages = [
        {"role": "system", "content": FINANCE_PROMPT},
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

                    result = await execute_tool(
                        tool_call.tool_name,
                        tool_call.arguments
                    )

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

            context["financial_plan"] = data
            return data

        except Exception as e:
            print("FINANCE AGENT ERROR:", e)
            raise
        
        
    

    