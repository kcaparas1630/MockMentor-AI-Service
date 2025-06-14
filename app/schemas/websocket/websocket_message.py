from pydantic import BaseModel
from typing import Literal

# Base model for all websocket messages
class WebSocketMessage(BaseModel):
    type: Literal["message", "error"]
    content: str

# Model for user messages
class WebSocketUserMessage(BaseModel):
    content: str
