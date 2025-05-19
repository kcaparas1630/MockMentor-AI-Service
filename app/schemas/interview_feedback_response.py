from pydantic import BaseModel, Field
from typing import List
from app.schemas.interview_request import InterviewRequest

class InterviewFeedbackResponse(InterviewRequest):
    overall_assessment: str
    strengths: List[str]
    areas_for_improvement: List[str]
    confidence_score: int
    recommended_actions: List[str]
