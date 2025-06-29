"""
Description: 
This module defines the schema for the interview feedback response.

Dependencies:
- pydantic: For data validation and settings management.
- typing: For type annotations.

Author: @kcaparas1630
"""
from pydantic import BaseModel, Field
from typing import List

class InterviewFeedbackResponse(BaseModel):
    score: int = Field(ge=0, le=10, description="Interview score between 0 and 10")
    feedback: str = Field(default="", description="Feedback on the interview")
    strengths: List[str] = Field(default=[], description="Strengths of the candidate")
    improvements: List[str] = Field(default=[], description="Areas for improvement")
    tips: List[str] = Field(default=[], description="Tips for the candidate")
