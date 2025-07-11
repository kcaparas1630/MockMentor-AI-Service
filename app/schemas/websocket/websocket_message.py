"""
Description: 
This module defines the schemas for WebSocket messages used in the application.

# WebsocketMessage Class is the base clas for all received messages from the server.
# WebSocketUserMessage Class is the schema for user messages sent to the server.

Dependencies:
- pydantic: For data validation and settings management.
- typing: For type annotations.

Author: @kcaparas1630
"""

from pydantic import BaseModel
from typing import Literal

# Base model for all websocket messages
class WebSocketMessage(BaseModel):
    type: Literal["message", "error", "transcript", "incremental_transcript", "heartbeat"]
    content: str

# Model for user messages
class WebSocketUserMessage(BaseModel):
    content: str
