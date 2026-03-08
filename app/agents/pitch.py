from openai import AsyncOpenAI
from pydantic import BaseModel


PITCH_PROMPT = """

You are a startup pitch generator.

Your job is to create a structured startup pitch using the provided information.

You will receive:

- market analysis
- technical architecture
- financial plan

Use this information to generate a compelling startup pitch.

Rules:
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
    idea = context["idea"]
    market_analysis = context["market_analysis"]
    tech_architecture = context["tech_architecture"]
    finance = context["financial_plan"]


    messages = [
        {"role": "system", "content": PITCH_PROMPT},
        {"role": "user", "content": json.dumps({
                "idea": idea,
                "market_analysis": market_analysis,
                "tech_architecture": tech_architecture,
                "financial_plan": finance
            })}
    ]
    
    response = await client.beta.chat.completions.parse(
        model = "liquid/lfm2.5-1.2b",
        messages = messages,
        response_format = PitchSchema
    )

    return response.choices[0].message.parsed


