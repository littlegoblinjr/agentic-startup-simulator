from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List
import json
from app.core.telemetry import get_telemetry

from app.core.llm_config import client, DEFAULT_MODEL

EVALUATION_PROMPT = """
You are a startup evaluator and venture capital analyst.

Your job is to evaluate a startup simulation's output. 
You will receive the market analysis, technical architecture, financial plan, and the final pitch.

Evaluate the startup on the following criteria:

1. Consistency (0-25 points):
   - Are the market, tech, and finance plans aligned? 
   - Does the pitch reflect the research?

2. Completeness (0-25 points):
   - Are all sections detailed and actionable?
   - Is there enough information for an investor to make a decision?

3. Realism & Innovation (0-25 points):
   - Are the financial projections realistic yet ambitious?
   - Is there a distinct 'unfair advantage' or innovative angle in the tech stack?

4. Strategic Addressing of Risks (0-25 points):
   - Are the identified market and tech risks addressed with specific, actionable mitigation strategies?

Return a structured scorecard in JSON:

{
  "total_score": 85,
  "criteria_scores": {
    "consistency": 20,
    "completeness": 22,
    "realism": 21,
    "risk_mitigation": 22
  },
  "feedback": {
    "strengths": ["point1", "point2"],
    "weaknesses": ["point1", "point2"],
    "investor_verdict": "A brief summary of whether this is a 'investable' idea based on the simulated research."
  }
}

Rules:
- Be objective and critical.
- Return ONLY valid JSON.
- All keys in double quotes.
"""

class CriteriaScores(BaseModel):
    consistency: int
    completeness: int
    realism: int
    risk_mitigation: int

class Feedback(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    investor_verdict: str

class EvaluationSchema(BaseModel):
    total_score: int
    criteria_scores: CriteriaScores
    feedback: Feedback

async def evaluation_agent(context):
    run_id = context.get("run_id")
    telemetry = get_telemetry(run_id, idea=context.get("idea")) if run_id else None

    # Gather all inputs for evaluation
    eval_input = {
        "idea": context.get("idea"),
        "market": context.get("market_analysis"),
        "tech": context.get("tech_architecture"),
        "finance": context.get("financial_plan"),
        "synthesis": context.get("synthesis"),
        "pitch": context.get("pitch")
    }

    if telemetry:
        telemetry.log_event("evaluation_agent", "evaluation_start", {"summary": "Evaluating final output"})

    messages = [
        {"role": "system", "content": EVALUATION_PROMPT},
        {"role": "user", "content": json.dumps(eval_input, default=str)}
    ]

    response = await client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=messages,
        response_format=EvaluationSchema
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    scorecard = response.choices[0].message.parsed
    if telemetry:
        telemetry.log_event("evaluation_agent", "final_scorecard", {"scorecard": "evaluation completed"}, usage=usage)

    # Ensure context receives a serializable dict, not a Pydantic object
    scorecard_dict = scorecard.dict() if hasattr(scorecard, "dict") else scorecard
    context["evaluation_scorecard"] = scorecard_dict
    return scorecard_dict
