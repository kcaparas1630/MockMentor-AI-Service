"""
Description: 
This module defines the UserMessage schema using Pydantic.

Dependencies:
- pydantic: For data validation and settings management.

Author: @kcaparas1630
"""

from pydantic import BaseModel

class UserMessage(BaseModel):
    session_id: str
    message: str 
