from pydantic import BaseModel
from typing import Dict, Any


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, any]