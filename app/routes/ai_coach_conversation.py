from fastapi import APIRouter, HTTPException
from app.services.main_conversation_service import MainConversationService
from app.schemas.main.interview_session import InterviewSession
from app.schemas.main.user_message import UserMessage
from loguru import logger

router = APIRouter(
    prefix="/api",
    tags=["ai-coach-conversation"]
)

@router.post("/ai-coach-conversation/start")
async def get_ai_coach_conversation(request: InterviewSession):
    """
    Get AI coach conversation for a given interview session
    """
    try:
        service = MainConversationService()
        response = await service.conversation_with_user_response(request)
        return response
    except Exception as e:
        logger.error(f"Error getting AI coach conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/ai-coach-conversation/message")
async def send_message_to_ai_coach(request: UserMessage):
    """
    Send a message to the AI coach
    """
    try:
        service = MainConversationService()
        response = await service.handle_user_message(request)
        return response
    except Exception as e:
        logger.error(f"Error sending message to AI coach: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
