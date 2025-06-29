"""
Description:
Interview session schema for the application.

Dependencies:
- pydantic: Used for data validation and settings management.

Author: @kcaparas1630
"""
from pydantic import BaseModel

class InterviewSession(BaseModel):
    session_id: str
    user_name: str
    jobRole: str
    jobLevel: str
    questionType: str
