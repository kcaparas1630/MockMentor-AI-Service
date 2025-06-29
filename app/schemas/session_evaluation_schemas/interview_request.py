"""
Description: 
Schema for interview request data.

Dependencies:
- pydantic: For data validation and settings management.

Author: @kcaparas1630
"""
from pydantic import BaseModel

class InterviewRequest(BaseModel):
    question: str
    answer: str
