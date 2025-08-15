"""
Description: 
This module defines the schema for an interview analysis request.

Dependencies:
- pydantic: For data validation and settings management.
- app.schemas.session_evaluation_schemas.interview_request: For the base interview request schema.
- app.schemas.session_evaluation_schemas.session_state: For SessionMetadata schema.

Author: @kcaparas1630
"""
from pydantic import Field
from app.schemas.session_evaluation_schemas.interview_request import InterviewRequest
from app.schemas.session_evaluation_schemas.session_state import SessionMetadata

class InterviewAnalysisRequest(InterviewRequest):
    session_metadata: SessionMetadata
    interviewType: str = Field(default="Behavioral")
