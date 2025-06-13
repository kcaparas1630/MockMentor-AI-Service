from pydantic import BaseModel

class InterviewSession(BaseModel):
    session_id: str
    user_name: str
    job_role: str
    job_level: str
    interview_type: str
