from openai import AsyncOpenAI
from pydantic import BaseModel
import json
from app.core.telemetry import get_telemetry

from app.core.llm_config import client, DEFAULT_MODEL


PITCH_PROMPT = """

You are a startup pitch generator.

Your job is to create a structured startup pitch using the provided information.

You will receive:

- market analysis
- technical architecture
- financial plan
- synthesis (cross-validation and unified strategy)

Use this information to generate a compelling, high-impact startup pitch.

Rules:
- **Startup Name**: Create a unique, catchy, and brandable name (e.g., 'TherapyGo' instead of 'AI Therapy App').
- Always return valid JSON
- Return ONLY JSON
- Do not include extra text


"""


class PitchSchema(BaseModel):

    startup_name: str
    problem: str
    solution: str
    target_market: str
    product: str
    business_model: str
    technology: str
    go_to_market: str
    financial_projection: str
    vision: str


async def pitch_agent(context):
    run_id = context.get("run_id")
    telemetry = get_telemetry(run_id, idea=context.get("idea")) if run_id else None

    idea = context["idea"]
    market_analysis = context["market_analysis"]
    tech_architecture = context["tech_architecture"]
    finance = context["financial_plan"]
    synthesis = context.get("synthesis", None)

    pitch_input = {
        "idea": idea,
        "market_analysis": market_analysis,
        "tech_architecture": tech_architecture,
        "financial_plan": finance,
    }
    if synthesis:
        pitch_input["synthesis"] = synthesis

    if telemetry:
        telemetry.log_event("pitch_agent", "generate_pitch_start", {"input_summary": "Context provided"})

    messages = [
        {"role": "system", "content": PITCH_PROMPT},
        {"role": "user", "content": json.dumps(pitch_input, default=str)}
    ]
    
    response = await client.beta.chat.completions.parse(
        #model = "liquid/lfm2.5-1.2b",
        model=DEFAULT_MODEL,
        messages = messages,
        response_format = PitchSchema
    )
    usage = response.usage.model_dump() if hasattr(response, "usage") else None
    output = response.choices[0].message.parsed
    if telemetry:
        telemetry.log_event("pitch_agent", "final_pitch", {"pitch_summary": "pitch generated"}, usage=usage)

    # Ensure context receives a serializable dict, not a Pydantic object
    output_dict = output.dict() if hasattr(output, "dict") else output
    context["pitch"] = output_dict

    return output_dict
