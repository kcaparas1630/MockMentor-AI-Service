from pydantic import BaseModel
from typing import Optional
from app.schemas.main.conversation_turn import ConversationTurn
from app.schemas.main.overall_feedback import OverallFeedback

class InterviewSession(BaseModel):
    session_id: str
    user_name: str
    job_role: str
    job_level: str
    interview_type: str
    # current_question_index: int
    # conversation_history: list[ConversationTurn]
    # overall_feedback: Optional[OverallFeedback] = None
