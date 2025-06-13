from pydantic import BaseModel

# Base model for all websocket messages
class WebSocketMessage(BaseModel):
    type: str  # "message", "error", "system"
    content: str

class WebSocketUserMessage(BaseModel):
    content: str
