from pydantic import BaseModel

class InterviewRequest(BaseModel):
    question: str
    answer: str
