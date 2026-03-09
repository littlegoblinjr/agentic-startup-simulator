from openai import AsyncOpenAI
from app.tools.schemas import ToolCall
from app.tools.executor import execute_tool
from typing import List
import json
FINANCE_PROMPT = """

You are a startup finance analyst.

Your job is to analyze the startup idea and produce a structured financial plan.

You may use the available tools if calculations are needed.

Available tools:

python_execute
Description: Execute Python code for financial calculations and projections.

Tool call format (JSON only):

{
  "tool_name": "python_execute",
  "arguments": {
    "code": "python code"
  }
}

Decision rule:

If financial projections or calculations are required,
you MUST call the python_execute tool.

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
- Either return a tool call OR the final financial JSON
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
            model="liquid/lfm2.5-1.2b",
            messages=messages
        )

        output = response.choices[0].message.content

        try:

            tool_call = ToolCall.model_validate_json(output)

            result = await execute_tool(
                tool_call.tool_name,
                tool_call.arguments
            )

            messages.append({"role": "assistant", "content": output})
            messages.append({"role": "tool", "content": json.dumps(result)})

        except Exception:
            context["financial_plan"] = output

            return output

    