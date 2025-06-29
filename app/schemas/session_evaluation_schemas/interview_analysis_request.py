"""
Description: 
This module defines the schema for an interview analysis request.

Dependencies:
- pydantic: For data validation and settings management.
- app.schemas.session_evaluation_schemas.interview_request: For the base interview request schema.

Author: @kcaparas1630
"""
from pydantic import Field
from app.schemas.session_evaluation_schemas.interview_request import InterviewRequest

class InterviewAnalysisRequest(InterviewRequest):
    jobRole: str = Field(default="Software Engineer")
    jobLevel: str = Field(default="Entry-Level")
    interviewType: str = Field(default="Behavioral")
    questionType: str = Field(default="Behavioral")
