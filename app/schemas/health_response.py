"""
Description: 
This module defines the schema for health check responses using Pydantic.

Dependencies:
- pydantic: For data validation and settings management.

Author: @kcaparas1630
"""
from pydantic import BaseModel

class HealthResponse(BaseModel):
    """
    Schema for health check endpoint responses.
    """
    status: str
