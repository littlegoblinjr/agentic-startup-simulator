from app.cache.semantic_cache import semantic_cached_search
from app.core.telemetry import get_telemetry
from app.core.utils import parse_llm_json
from app.memory.vector_store import rerank, retrieve_memory
from openai import AsyncOpenAI
from app.tools.schemas import ToolCall
from app.tools.executor import execute_tool
from typing import List
import json
from pydantic import BaseModel

from app.core.llm_config import client, DEFAULT_MODEL

async def batch_summarize_results(idea, results, extract_section, telemetry=None):
    """Summarize financial results in small batches for 4096 context limits."""
    chunks = []
    for res in results:
        if isinstance(res, dict) and "results" in res:
            for doc in res["results"]:
                chunks.extend(doc.get("relevant_chunks", []))

    if not chunks:
        if telemetry: telemetry.log_event("finance_agent", "batch_summarize_skip", {"reason": "no chunks"})
        return []

    batch_size = 3
    summaries = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        combined_text = "\n\n".join(batch)[:3000]
        try:
            summary_response = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "Summarize financial benchmarks and pricing insights into 3-5 bullet points."},
                    {"role": "user", "content": f"Idea: {idea}\nFocus: {extract_section}\nText:\n{combined_text}"}
                ],
                max_tokens=250
            )
            usage = summary_response.usage.model_dump() if hasattr(summary_response, "usage") else None
            if telemetry: telemetry.log_event("finance_agent", "batch_summarize_success", {"summary": summary_response.choices[0].message.content[:50]}, usage=usage)
            summaries.append(summary_response.choices[0].message.content.strip())
        except Exception as e:
            if telemetry: telemetry.log_event("finance_agent", "batch_summarize_error", {"error": str(e)})
            continue

    return summaries

FINANCE_PROMPT = """
You are a startup finance analyst. Your job is to analyze a startup idea and produce a structured financial plan.

You MUST perform web_search at least once.

Return the final financial analysis in JSON:
{
  "revenue_model": "description",
  "pricing_strategy": "description",
  "cost_structure": "description",
  "break_even_estimate": "description",
  "financial_projection": "description"
}

Rules:
- Return ONLY JSON.
- Focus on specific pricing, costs, and revenue models for the given idea.
"""

FINAL_FINANCE_PROMPT = """
Produce the final financial analysis in JSON.
Schema:
{
  "revenue_model": "description",
  "pricing_strategy": "description",
  "cost_structure": "description",
  "break_even_estimate": "description",
  "financial_projection": "description"
}
"""

FINANCE_QUERY_PROMPT = """
Generate 3 financial search queries (4-7 words). Return as JSON list.
"""

class QuerySchema(BaseModel):
    queries: List[str]

class FinanceAnalysisSchema(BaseModel):
    revenue_model: str
    pricing_strategy: str
    cost_structure: str
    break_even_estimate: str
    financial_projection: str

async def finance_agent(context):
    run_id = context.get("run_id")
    telemetry = get_telemetry(run_id, idea=context.get("idea")) if run_id else None
    idea = context["idea"]
    market_analysis = context.get("market_analysis", {})

    if telemetry: telemetry.log_event("finance_agent", "start", {"idea": idea})

    # 1. Knowledge Retrieval
    response = await client.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": FINANCE_QUERY_PROMPT}, {"role": "user", "content": f"Idea: {idea}"}],
        response_format=QuerySchema
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    finance_queries = response.choices[0].message.parsed.queries
    if telemetry: telemetry.log_event("finance_agent", "generate_queries", {"queries": finance_queries}, usage=usage)
    
    useful_memory = []
    for q in finance_queries:
        rows = await retrieve_memory(q, memory_type="financial_plan")
        ranked = await rerank(q, rows, telemetry=telemetry)
        for r in ranked:
            if r.get("rerank_score", 0) > 0.6:
                useful_memory.append(r["content"])
                if telemetry: telemetry.log_event("finance_agent", "memory_hit", {"query": q, "content_summary": r["content"][:100]})

    memory_context = "\n".join(useful_memory[:3]) if useful_memory else "No relevant memories."

    # 2. Main Loop
    messages = [
        {"role": "system", "content": FINANCE_PROMPT},
        {"role": "system", "content": f"Existing Financial Evidence:\n{memory_context}"},
        {"role": "user", "content": f"Market Analysis: {json.dumps(market_analysis)}\nIdea: {idea}"}
    ]
    
    refinement_done = False
    all_summaries = []
    combined_findings = ""

    for round_idx in range(3):
        try:
            response = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages
            )
            output = response.choices[0].message.content
            usage = response.usage.model_dump() if hasattr(response, "usage") else None
            if telemetry: telemetry.log_event("finance_agent", f"round_{round_idx}_output", {"output": output[:100] + "..."}, usage=usage)
            
            data = parse_llm_json(output)

            if "tool_calls" in data:
                results = []
                for call in data["tool_calls"]:
                    tool_call = ToolCall(**call)
                    if tool_call.tool_name == "web_search":
                        if telemetry: telemetry.log_event("finance_agent", "tool_call", {"tool": "web_search", "query": tool_call.arguments["query"]})
                        res = await semantic_cached_search(tool_call.arguments["query"])
                        results.append(res)
                    elif tool_call.tool_name == "python_execute":
                        if telemetry: telemetry.log_event("finance_agent", "tool_call", {"tool": "python_execute"})
                        res = await execute_tool("python_execute", tool_call.arguments)
                        results.append({"query": "python_calculation", "results": [{"relevant_chunks": [str(res)]}]})
                
                # Batch summarize
                batch_summaries = await batch_summarize_results(idea, results, "revenue, pricing, costs", telemetry=telemetry)
                all_summaries.extend(batch_summaries)
                
                # 🛡️ TRUNCATE HISTORY
                combined_findings = "\n\n".join(all_summaries[-4:])
                if telemetry: telemetry.log_event("finance_agent", "consolidated_findings_update", {"summary_count": len(all_summaries)})
                
                messages = [
                    {"role": "system", "content": FINANCE_PROMPT},
                    {"role": "system", "content": f"Consolidated Financial Findings:\n{combined_findings}"},
                    {"role": "user", "content": f"Market Context: {json.dumps(market_analysis)}\nContinue Financial Plan for: {idea}"}
                ]
                continue

            context["financial_plan"] = data
            if telemetry: telemetry.log_event("finance_agent", "success", {"plan": data})
            return data

        except Exception as e:
            if telemetry: telemetry.log_event("finance_agent", "error", {"round": round_idx, "error": str(e)})
            if "overflow" in str(e).lower():
                all_summaries = all_summaries[-2:]
                continue
            raise

    # Final Forcing
    final_response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": FINAL_FINANCE_PROMPT}, {"role": "user", "content": f"Findings: {combined_findings}"}],
        response_format=FinanceAnalysisSchema
    )
    usage = final_response.usage.model_dump() if hasattr(final_response, "usage") else None
    result = final_response.choices[0].message.parsed
    if telemetry: telemetry.log_event("finance_agent", "final_forcing_success", {"plan": result.dict() if hasattr(result, 'dict') else result}, usage=usage)
    
    # Ensure context receives a serializable dict, not a Pydantic object
    result_dict = result.dict() if hasattr(result, "dict") else result
    context["financial_plan"] = result_dict
    return result_dict