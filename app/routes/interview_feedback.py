from fastapi import APIRouter, HTTPException
from app.schemas.text_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.schemas.text_schemas.interview_feedback_response import InterviewFeedbackResponse
from app.services.text_answers_service import TextAnswersService
from loguru import logger
import asyncio

router = APIRouter(
    prefix="/api",
    tags=["interview-feedback"]
)


@router.post("/interview-feedback", response_model=InterviewFeedbackResponse)
async def get_interview_feedback(request: InterviewAnalysisRequest):
    """
    Get interview feedback for a given question and user response
    """
    try:
        service = TextAnswersService()
        feedback = await service.analyze_interview_response(request)
        
        return feedback
    except Exception as e:
        logger.error(f"Error getting interview feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
        