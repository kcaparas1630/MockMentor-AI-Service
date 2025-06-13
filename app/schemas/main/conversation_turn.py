from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.text_schemas.interview_request import InterviewRequest

class ConversationTurn(BaseModel):
    turn_number: int
    question: str
    user_response: str
    feedback: str
    timestamp: datetime
    response_time_seconds: Optional[float] = None
