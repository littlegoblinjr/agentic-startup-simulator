import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Centralized OpenAI-Compatible client
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", None) # Allows using Groq, Together, vLLM, etc.
)

# Unified model selection
# Defaults to 'qwen2.5-3b-instruct' but can be overridden in .env
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-3b-instruct")
PARSING_MODEL = os.getenv("PARSING_MODEL", DEFAULT_MODEL)

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
    },
    "qwen2.5-3b-instruct": {
        "input": 0.0, # Adjust if using a paid provider
        "output": 0.0
    }
}
