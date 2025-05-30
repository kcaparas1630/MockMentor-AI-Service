from pydantic import Field
from app.schemas.interview_request import InterviewRequest

class InterviewAnalysisRequest(InterviewRequest):
    jobRole: str = Field(default="Software Engineer")
    jobLevel: str = Field(default="Entry-Level")
    interviewType: str = Field(default="Behavioral")
    questionType: str = Field(default="Behavioral")
