from pydantic import BaseModel, Field
from typing import List

class InterviewFeedbackResponse(BaseModel):
    score: int
    feedback: str
    strengths: List[str]
    improvements: List[str]
    tips: List[str]
