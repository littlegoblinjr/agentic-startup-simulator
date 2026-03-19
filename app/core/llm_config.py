import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Centralized OpenAI client
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Unified model selection
# Recommended: 'gpt-4o-mini' for high-performance, cost-effective agentic workflows.
DEFAULT_MODEL = "gpt-4o-mini"
PARSING_MODEL = "gpt-4o-mini" # Both same for consistency

# Pricing for OpenAI Models (Price per 1M tokens)
# Source: https://openai.com/api/pricing/
MODEL_PRICING = {
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00
    }
}
