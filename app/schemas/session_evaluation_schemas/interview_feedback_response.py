"""
Description: 
This module defines the schema for the interview feedback response.

Dependencies:
- pydantic: For data validation and settings management.
- typing: For type annotations.

Author: @kcaparas1630
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class FollowUpQuestionDetails(BaseModel):
    original_question: Optional[str] = Field(None, description="Original question text for follow-up")
    specific_gap_identified: Optional[str] = Field(None, description="Specific gap to address for the follow-up")

class NextAction(BaseModel):
    type: str = Field(..., description="Type of next action: 'continue', 'retry_question', 'ask_follow_up', 'suggest_exit'")
    message: str = Field(..., description="Message to the user for the next turn")
    follow_up_question_details: Optional[FollowUpQuestionDetails] = Field(None, description="Details for a follow-up question, if applicable")

class InterviewFeedbackResponse(BaseModel):
    score: int = Field(ge=0, le=10, description="Interview score between 0 and 10")
    feedback: str = Field(default="", description="Feedback on the interview")
    strengths: List[str] = Field(default=[], description="Strengths of the candidate")
    improvements: List[str] = Field(default=[], description="Areas for improvement")
    tips: List[str] = Field(default=[], description="Tips for the candidate")
    engagement_check: bool = Field(False, description="True if candidate shows lack of serious engagement")
    technical_issue_detected: bool = Field(False, description="True if a technical issue was detected")
    needs_retry: bool = Field(False, description="True if the user needs to retry the question")
    next_action: NextAction = Field(..., description="Defines the AI's next conversational action")

class InterviewFeedbackFormatterResponse(BaseModel):
    score: int = Field(ge=0, le=10, description="Interview score between 0 and 10")
    feedback: str = Field(default="", description="Feedback on the interview")
    strengths: List[str] = Field(default=[], description="Strengths of the candidate")
    improvements: List[str] = Field(default=[], description="Areas for improvement")
    tips: List[str] = Field(default=[], description="Tips for the candidate")
