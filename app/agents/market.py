from app.cache.semantic_cache import semantic_cached_search
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.tools.schemas import ToolCall
from typing import List
from app.tools.executor import execute_tool
from app.memory.vector_store import rerank, retrieve_memory
from app.core.utils import parse_llm_json
from app.core.telemetry import get_telemetry
import json

from app.core.llm_config import client, DEFAULT_MODEL

MARKET_PROMPT = """
You are a market research agent. Your job is to analyze a startup idea and produce a structured market analysis.

You MUST perform web_search at least once before producing the final answer.

Research guidelines:
1. Target users (demographics, needs)
2. Market size (TAM/SAM, growth trends)
3. Competitors (Identify 4-6 specific players)
4. Market trends & gaps

Tool call format (JSON only):
{
  "tool_calls": [
    {
      "tool_name": "web_search",
      "arguments": {"query": "search query"}
    }
  ]
}

When you have enough information, return the final analysis in JSON:
{
  "target_audience": "description",
  "market_size": "description",
  "competitors": ["company1", "company2"],
  "market_trends": ["trend1", "trend2"],
  "opportunities": ["opportunity1", "opportunity2"],
  "risks": ["risk1", "risk2"]
}

Rules:
- Return ONLY JSON.
- Either return tool calls OR the final market analysis.
- Focus on the specific idea, do not generalize.
"""

FINAL_MARKET_ANALYSIS_PROMPT = """
Analyze the startup idea and produce a structured market analysis in JSON. 
Provide a detailed target audience, market size, 4-6 competitors, trends, opportunities, and risks.

Schema:
{
  "target_audience": "description",
  "market_size": "description",
  "competitors": ["company1", "company2"],
  "market_trends": ["trend1", "trend2"],
  "opportunities": ["opportunity1", "opportunity2"],
  "risks": ["risk1", "risk2"]
}
"""

MULTI_QUERY_RETRIEVAL_PROMPT = """
Generate 5 short (4-7 words) search queries for market research. Return as JSON list.
Target: competitors, market size, trends, similar apps, startup examples.
"""

REFINEMENT_PROMPT = """
Improve the following research results by generating 2 deeper search queries. Return as JSON list.
"""

class QuerySchema(BaseModel):
    queries: List[str]

class Final_Market_Analysis_Schema(BaseModel):
    target_audience: str
    market_size: str
    competitors: List[str]
    market_trends: List[str]
    opportunities: List[str]
    risks: List[str]

async def batch_summarize_results(idea, results, extract_section, telemetry=None):
    """Summarize web search result chunks in small batches to avoid token overflows."""
    chunks = []
    for res in results:
        if isinstance(res, dict) and "results" in res:
            for doc in res["results"]:
                chunks.extend(doc.get("relevant_chunks", []))

    if not chunks:
        if telemetry: telemetry.log_event("market_agent", "batch_summarize_skip", {"reason": "no chunks found"})
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
                    {"role": "system", "content": "Summarize market insights into 3-5 bullet points. Be very concise."},
                    {
                        "role": "user",
                        "content": f"Idea: {idea}\nFocus: {extract_section}\nText:\n{combined_text}"
                    }
                ],
                max_tokens=250
            )
            usage = summary_response.usage.model_dump() if hasattr(summary_response, "usage") else None
            if telemetry: telemetry.log_event("market_agent", "batch_summarize_success", {"summary": summary_response.choices[0].message.content[:50]}, usage=usage)
            summaries.append(summary_response.choices[0].message.content.strip())
        except Exception as e:
            if telemetry: telemetry.log_event("market_agent", "batch_summarize_error", {"error": str(e)})
            continue

    return summaries

async def market_agent(context):
    run_id = context.get("run_id")
    telemetry = get_telemetry(run_id, idea=context.get("idea")) if run_id else None
    idea = context["idea"]
    
    if telemetry: telemetry.log_event("market_agent", "start", {"idea": idea})

    # 1. Multi-query Knowledge Retrieval
    response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": MULTI_QUERY_RETRIEVAL_PROMPT}, {"role": "user", "content": idea}],
        response_format=QuerySchema
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    market_queries = response.choices[0].message.parsed.queries
    if telemetry: telemetry.log_event("market_agent", "generate_queries", {"queries": market_queries}, usage=usage)
    
    useful_memory = []
    for q in market_queries:
        rows = await retrieve_memory(q, memory_type="market_analysis")
        reranked = await rerank(q, rows, telemetry=telemetry)
        for r in reranked:
            if r.get("rerank_score", 0) > 0.6:
                useful_memory.append(r["content"])
                if telemetry: telemetry.log_event("market_agent", "memory_hit", {"query": q, "content_summary": r["content"][:100]})

    memory_context = "\n".join(useful_memory[:3]) if useful_memory else "No relevant memories."
    
    # 2. Main Research Loop
    messages = [
        {"role": "system", "content": MARKET_PROMPT},
        {"role": "system", "content": f"Existing Evidence:\n{memory_context}"},
        {"role": "user", "content": f"Startup Idea: {idea}"}
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
            if telemetry: telemetry.log_event("market_agent", f"round_{round_idx}_output", {"output": output[:100] + "..."}, usage=usage)
            
            data = parse_llm_json(output)

            if "tool_calls" in data:
                results = []
                for call in data["tool_calls"]:
                    tool_call = ToolCall(**call)
                    if tool_call.tool_name == "web_search":
                        if telemetry: telemetry.log_event("market_agent", "tool_call", {"tool": "web_search", "query": tool_call.arguments["query"]})
                        res = await semantic_cached_search(tool_call.arguments["query"])
                        results.append(res)
                
                # Refine queries if first round
                if not refinement_done:
                    refinement_done = True
                    try:
                        refine_res = await client.beta.chat.completions.parse(
                            model=DEFAULT_MODEL,
                            messages=[{"role": "system", "content": REFINEMENT_PROMPT}, {"role": "user", "content": json.dumps(results[:2])}],
                            response_format=QuerySchema
                        )
                        refine_usage = refine_res.usage.model_dump() if hasattr(refine_res, "usage") else None
                        for rq in refine_res.choices[0].message.parsed.queries:
                            if telemetry: telemetry.log_event("market_agent", "refined_query", {"query": rq}, usage=refine_usage)
                            r = await semantic_cached_search(rq)
                            results.append(r)
                    except: pass

                # Batch summarize findings
                batch_summaries = await batch_summarize_results(idea, results, "market size, competitors, trends", telemetry=telemetry)
                all_summaries.extend(batch_summaries)
                
                # 🛡️ TRUNCATE HISTORY TO FIT 4096
                combined_findings = "\n\n".join(all_summaries[-5:])
                if telemetry: telemetry.log_event("market_agent", "consolidated_findings_update", {"summary_count": len(all_summaries)})
                
                messages = [
                    {"role": "system", "content": MARKET_PROMPT},
                    {"role": "system", "content": f"Consolidated Research Findings:\n{combined_findings}"},
                    {"role": "user", "content": f"Based on the findings above, continue the analysis for: {idea}"}
                ]
                continue

            context["market_analysis"] = data
            if telemetry: telemetry.log_event("market_agent", "success", {"analysis": data})
            return data

        except Exception as e:
            if telemetry: telemetry.log_event("market_agent", "error", {"round": round_idx, "error": str(e)})
            if "overflow" in str(e).lower():
                all_summaries = all_summaries[-2:]
                continue
            raise

    # Final Forcing
    final_response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=[{"role": "system", "content": FINAL_MARKET_ANALYSIS_PROMPT}, {"role": "user", "content": f"Idea: {idea}\nFindings: {combined_findings}"}],
        response_format=Final_Market_Analysis_Schema
    )
    usage = final_response.usage.model_dump() if hasattr(final_response, "usage") else None
    result = final_response.choices[0].message.parsed
    if telemetry: telemetry.log_event("market_agent", "final_forcing_success", {"analysis": result.dict() if hasattr(result, 'dict') else result}, usage=usage)
    
    # Ensure context receives a serializable dict, not a Pydantic object
    result_dict = result.dict() if hasattr(result, "dict") else result
    context["market_analysis"] = result_dict
    return result_dict