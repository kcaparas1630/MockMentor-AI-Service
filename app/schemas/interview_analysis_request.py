from pydantic import BaseModel, Field
from app.schemas.interview_request import InterviewRequest

class InterviewAnalysisRequest(InterviewRequest):
    job_role: str = Field(default="Software Engineer")
    job_level: str = Field(default="Entry-Level")
    interview_type: str = Field(default="Behavioral")
    
