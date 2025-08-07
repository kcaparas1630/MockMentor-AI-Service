"""
Description:
Interview session schema for the application.

Dependencies:
- pydantic: Used for data validation and settings management.

Author: @kcaparas1630
"""
from pydantic import BaseModel, Field
from typing import Optional

class InterviewSession(BaseModel):
    session_id: str
    user_name: str
    jobRole: str
    jobLevel: str
    questionType: str
    custom_instruction: Optional[str] = Field(None, max_length=1000)