"""
User Message Handler Utility Module

This module provides functionality to handle individual user messages in an ongoing
interview session. It processes user input and generates appropriate AI responses
through the main conversation service.

The module contains a single async function that bridges user messages with the
main conversation service, ensuring proper context management and response generation
for ongoing interview conversations.

Dependencies:
- app.schemas.main.user_message: For user message data models.
- app.services.main_conversation.main_conversation_service: For conversation management.
- loguru: For logging operations.
- app.errors.exceptions import InternalServerError

Author: @kcaparas1630
"""

from app.schemas.main.user_message import UserMessage
from app.services.main_conversation.main_conversation_service import MainConversationService
from loguru import logger
from app.errors.exceptions import InternalServerError
from typing import Tuple, Dict, Any

async def handle_user_message(user_message: UserMessage) -> Tuple[str, Dict[str, Any]]:
    """
    Handle a user's message in an ongoing interview session.
    
    This function processes user messages by using the continue_conversation method
    which only requires session_id and user message for ongoing conversations.
    
    Args:
        user_message (UserMessage): The user's message object containing the session ID
            and message content.
            
    Returns:
        Tuple[str, Dict[str, Any]]: A tuple containing the AI's response and the session state.
        
    Raises:
        Exception: If there's an error processing the message or generating the response.
        
    Example:
        >>> user_msg = UserMessage(session_id="123", message="I'm ready to start")
        >>> response, state = await handle_user_message(user_msg)
        >>> print(response)  # AI's response to the user
        >>> print(state)     # Current session state
    """
    try:
        service = MainConversationService()
        response = await service.continue_conversation(user_message.session_id, user_message.message)
        session_state = service._session_state.get(user_message.session_id, {})
        return response, session_state
        
    except InternalServerError:
        raise
    except Exception as e:
        logger.error(f"Error in handle_user_message: {e}")
        raise InternalServerError("An unexpected error occurred while handling the user message.")
