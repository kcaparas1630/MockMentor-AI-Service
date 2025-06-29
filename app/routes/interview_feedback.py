"""
Interview Feedback API Route

Description:
This module defines a FastAPI route for analyzing interview responses and providing feedback.

Arguments:
- request: An instance of InterviewAnalysisRequest containing the user's response and question.

Returns:
- An instance of InterviewFeedbackResponse containing structured feedback data.

Dependencies:
- fastapi: For creating the FastAPI application and defining routes.
- app.schemas.session_evaluation_schemas.interview_analysis_request: For defining the request schema.
- app.schemas.session_evaluation_schemas.interview_feedback_response: For defining the response schema.
- app.services.text_answers_service: For processing the interview response and generating feedback.
- loguru: For logging information about the request and any errors that occur.

Author: @kcaparas1630

"""
from fastapi import APIRouter, HTTPException
from ..schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from ..schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse
from ..services.speech_to_text.text_answers_service import TextAnswersService
from loguru import logger

router = APIRouter(
    prefix="/api",
    tags=["interview-feedback"],
    responses={404: {"description": "Not found"}}
)


@router.post("/interview-feedback", response_model=InterviewFeedbackResponse)
async def get_interview_feedback(request: InterviewAnalysisRequest):
    """
    Get interview feedback for a given question and user response
    """
    try:
        service = TextAnswersService()
        feedback = await service.analyze_response(request)
        
        return feedback
    except Exception as e:
        logger.error(f"Error getting interview feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
        