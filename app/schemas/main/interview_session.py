from pydantic import BaseModel

class InterviewSession(BaseModel):
    session_id: str
    user_name: str
    jobRole: str # WIll change to match python naming conventions.
    jobLevel: str
    questionType: str
