from pydantic import BaseModel
from datetime import datetime

class OverallFeedback(BaseModel):
    overall_score: int
    strengths: list[str]
    improvements: list[str]
    tips: list[str]
    feedback: str
    timestamp: datetime
