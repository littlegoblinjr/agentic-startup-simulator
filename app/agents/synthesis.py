from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List
from app.core.utils import parse_llm_json
from app.core.telemetry import get_telemetry
import json


from app.core.llm_config import client, DEFAULT_MODEL


SYNTHESIS_PROMPT = """
You are a startup strategy synthesizer.

You are given outputs from:
- Market analysis
- Financial planning
- Technical architecture

Your job is to:

1. Check consistency across all outputs
   - Do pricing, target users, and costs align?
   - Are there contradictions between market and finance assumptions?
   - Does the tech architecture match the scale the market demands?

2. Identify gaps or weak assumptions
   - Missing risks
   - Unrealistic projections
   - Technical or financial blind spots
   - Misaligned business model for the target audience

3. Produce a unified startup strategy
   - Synthesize all three into a coherent, actionable plan
   - Be critical, not agreeable

Return JSON using EXACTLY this schema:

{
  "consistency_issues": ["issue1", "issue2"],
  "gaps": ["gap1", "gap2"],
  "refined_strategy": "coherent combined plan in 3-5 sentences",
  "key_risks": ["risk1", "risk2"],
  "recommendations": ["action1", "action2"]
}

Rules:
- Be critical and analytical, not agreeable
- Do NOT repeat inputs verbatim
- Focus on cross-analysis, not individual summaries
- Return ONLY valid JSON
- All keys MUST be enclosed in double quotes.
- Do NOT include explanations or markdown outside JSON
"""

FINAL_SYNTHESIS_PROMPT = """
You are a startup strategy synthesizer.

Given market analysis, financial planning, and technical architecture outputs,
produce a unified cross-analysis identifying contradictions, gaps, and a refined strategy.

Return JSON using EXACTLY this schema:

{
  "consistency_issues": ["issue1", "issue2"],
  "gaps": ["gap1", "gap2"],
  "refined_strategy": "coherent combined plan",
  "key_risks": ["risk1", "risk2"],
  "recommendations": ["action1", "action2"]
}

Rules:
- Return ONLY valid JSON
- All keys in double quotes
- No markdown or explanation outside JSON
"""

FINANCE_REFINEMENT_PROMPT = """
You are a startup finance analyst.

Your previous financial plan had the following issues identified by a cross-analysis:

{issues}

Revise the financial plan to address these issues.

Original plan:
{original}

Market context:
{market}

Return a revised financial plan in EXACTLY this JSON schema:

{{
  "revenue_model": "description",
  "pricing_strategy": "description",
  "cost_structure": "description",
  "break_even_estimate": "description",
  "financial_projection": "description"
}}

Rules:
- Return ONLY valid JSON
- Address the specific issues listed above
- Be realistic and internally consistent
- All keys in double quotes
"""

TECH_REFINEMENT_PROMPT = """
You are a technical architect.

Your previous technical architecture had the following issues identified by a cross-analysis:

{issues}

Revise the technical architecture to address these issues.

Original architecture:
{original}

Market context:
{market}

Return a revised architecture in EXACTLY this JSON schema:

{{
  "architecture": "description",
  "tech_stack": ["tech1", "tech2"],
  "database": "description",
  "deployment": "description",
  "scalability": "description",
  "security": "description"
}}

Rules:
- Return ONLY valid JSON
- Address the specific issues listed above
- Be realistic about infrastructure costs
- All keys in double quotes
"""


class SynthesisSchema(BaseModel):
    consistency_issues: List[str]
    gaps: List[str]
    refined_strategy: str
    key_risks: List[str]
    recommendations: List[str]


def _classify_issues(issues: list) -> tuple:
    """
    Split consistency issues into finance-related and tech-related buckets.
    Ambiguous issues go to both.
    """
    finance_keywords = {
        "pricing", "revenue", "cost", "profit", "subscription", "fee",
        "financial", "budget", "margin", "break-even", "projection", "model", "monetiz"
    }
    tech_keywords = {
        "infrastructure", "architecture", "database", "scalability", "stack",
        "deploy", "server", "api", "latency", "gpu", "compute", "tech", "system", "infra"
    }

    finance_issues, tech_issues = [], []
    for issue in issues:
        lower = issue.lower()
        is_finance = any(kw in lower for kw in finance_keywords)
        is_tech = any(kw in lower for kw in tech_keywords)
        if is_finance:
            finance_issues.append(issue)
        if is_tech:
            tech_issues.append(issue)
        if not is_finance and not is_tech:
            # Ambiguous — send to both agents
            finance_issues.append(issue)
            tech_issues.append(issue)

    return finance_issues, tech_issues


async def _refine_finance(original_finance, market, issues: list, telemetry=None) -> dict:
    """Ask the LLM to revise the financial plan given specific critique."""
    prompt = FINANCE_REFINEMENT_PROMPT.format(
        issues="\n".join(f"- {i}" for i in issues),
        original=json.dumps(original_finance, default=str),
        market=json.dumps(market, default=str)
    )
    if telemetry:
        telemetry.log_event("synthesis_agent", "refine_finance_start", {"issues": issues})
    
    print("REFINEMENT LOOP: revising finance plan with feedback...")
    response = await client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    output = response.choices[0].message.content
    try:
        refined = parse_llm_json(output)
        if telemetry:
            telemetry.log_event("synthesis_agent", "refine_finance_success", {"refined_summary": "finance refined"}, usage=usage)
        return refined
    except Exception as e:
        print("REFINEMENT LOOP: finance refinement parse failed, keeping original:", e)
        if telemetry:
            telemetry.log_event("synthesis_agent", "refine_finance_fail", {"raw": output})
        return original_finance


async def _refine_tech(original_tech, market, issues: list, telemetry=None) -> dict:
    """Ask the LLM to revise the tech architecture given specific critique."""
    prompt = TECH_REFINEMENT_PROMPT.format(
        issues="\n".join(f"- {i}" for i in issues),
        original=json.dumps(original_tech, default=str),
        market=json.dumps(market, default=str)
    )
    if telemetry:
        telemetry.log_event("synthesis_agent", "refine_tech_start", {"issues": issues})

    print("REFINEMENT LOOP: revising tech architecture with feedback...")
    response = await client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    output = response.choices[0].message.content
    try:
        refined = parse_llm_json(output)
        if telemetry:
            telemetry.log_event("synthesis_agent", "refine_tech_success", {"refined_summary": "tech refined"}, usage=usage)
        return refined
    except Exception as e:
        print("REFINEMENT LOOP: tech refinement parse failed, keeping original:", e)
        if telemetry:
            telemetry.log_event("synthesis_agent", "refine_tech_fail", {"raw": output})
        return original_tech


async def _run_synthesis(data: dict, telemetry=None, round_num=1) -> dict:
    """Run one synthesis pass with retries. Returns parsed dict or None on failure."""
    messages = [
        {"role": "system", "content": SYNTHESIS_PROMPT},
        {"role": "user", "content": json.dumps(data, default=str)}
    ]
    
    if telemetry:
        telemetry.log_event("synthesis_agent", f"round_{round_num}_start", {"data_summary": "Initial inputs"})

    for attempt in range(3):
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages
        )
        usage = response.usage.model_dump() if hasattr(response, "usage") else None
        output = response.choices[0].message.content
        print(f"SYNTHESIS ROUND {round_num} RAW OUTPUT:", output[:100] + "...")
        try:
            result = parse_llm_json(output)
            required = {"consistency_issues", "gaps", "refined_strategy", "key_risks", "recommendations"}
            if required.issubset(result.keys()):
                if telemetry:
                    telemetry.log_event("synthesis_agent", f"round_{round_num}_success", {"result_summary": "synthesis completed"}, usage=usage)
                return result
            missing = required - result.keys()
            print(f"SYNTHESIS: missing keys {missing}, retrying...")
            messages.append({"role": "assistant", "content": output})
            messages.append({
                "role": "user",
                "content": f"Missing keys: {missing}. Return complete JSON with all required keys."
            })
        except Exception as e:
            print(f"SYNTHESIS ERROR (attempt {attempt + 1}):", e)
            messages.append({"role": "assistant", "content": output})
            messages.append({
                "role": "user",
                "content": "Invalid JSON. Return ONLY valid JSON matching the required schema."
            })

    return None


async def synthesis_agent(context):
    """
    Cross-checks market, finance, and tech outputs for consistency and gaps.
    """
    run_id = context.get("run_id")
    telemetry = get_telemetry(run_id, idea=context.get("idea")) if run_id else None

    market  = context.get("market_analysis")
    finance = context.get("financial_plan")
    tech    = context.get("tech_architecture")

    data = {
        "idea":    context["idea"],
        "market":  market,
        "finance": finance,
        "tech":    tech,
    }

    # ── Round 1: initial synthesis ─────────────────────────────────────────
    result = await _run_synthesis(data, telemetry=telemetry, round_num=1)

    if result is None:
        print("SYNTHESIS AGENT: forcing structured final response")
        response = await client.beta.chat.completions.parse(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": FINAL_SYNTHESIS_PROMPT},
                {"role": "user",   "content": json.dumps(data, default=str)}
            ],
            response_format=SynthesisSchema
        )
        usage = response.usage.model_dump() if hasattr(response, "usage") else None
        result = response.choices[0].message.parsed
        if telemetry:
            telemetry.log_event("synthesis_agent", "fallback_success", {"result_summary": "synthesis fallback success"}, usage=usage)
        
        # Ensure context receives a serializable dict, not a Pydantic object
        result_dict = result.dict() if hasattr(result, "dict") else result
        context["synthesis"] = result_dict
        return result_dict

    issues = result.get("consistency_issues", [])

    # ── Refinement round (only when issues exist) ──────────────────────────
    if issues:
        print(f"REFINEMENT LOOP: {len(issues)} issue(s) found → refining agents...")
        finance_issues, tech_issues = _classify_issues(issues)

        refined_finance = finance
        refined_tech    = tech

        if finance_issues:
            refined_finance = await _refine_finance(finance, market, finance_issues, telemetry=telemetry)
            context["financial_plan"] = refined_finance

        if tech_issues:
            refined_tech = await _refine_tech(tech, market, tech_issues, telemetry=telemetry)
            context["tech_architecture"] = refined_tech

        # ── Round 2: re-synthesize ─────────────────────────────────────────
        print("REFINEMENT LOOP: re-running synthesis on refined outputs...")
        refined_data = {
            "idea":    context["idea"],
            "market":  market,
            "finance": refined_finance,
            "tech":    refined_tech,
        }
        refined_result = await _run_synthesis(refined_data, telemetry=telemetry, round_num=2)
        if refined_result:
            result = refined_result
            print("REFINEMENT LOOP: synthesis improved ✓")
        else:
            print("REFINEMENT LOOP: re-synthesis failed, keeping round-1 result")
    else:
        print("SYNTHESIS AGENT: no consistency issues → skipping refinement round")

    # Ensure context receives a serializable dict, not a Pydantic object
    result_dict = result.dict() if hasattr(result, "dict") else result
    context["synthesis"] = result_dict
    return result_dict
