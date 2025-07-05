"""
WebSocket Connection Handler Utility Module

This module provides functionality to handle the complete WebSocket connection lifecycle
for interview sessions. It manages the initial connection setup, ongoing message processing,
and proper connection cleanup.

The module contains a single async function that orchestrates the entire WebSocket conversation,
including session initialization, message handling, and error management. It serves as the
primary entry point for WebSocket-based interview sessions.

Dependencies:
- starlette.websockets: For WebSocket connection handling.
- loguru: For logging operations.
- app.schemas.websocket.websocket_message: For WebSocket message models.
- app.schemas.main.interview_session: For interview session data models.
- app.schemas.main.user_message: For user message data models.
- app.services.main_conversation.main_conversation_service: For conversation management.
- app.services.main_conversation.tools.websocket_utils.handle_user_message: For processing individual user messages.
- app.services.transcription.transcriber: For transcribing audio.
- app.errors.exceptions: For InternalServerError handling.

Author: @kcaparas1630
"""

from starlette.websockets import WebSocket, WebSocketDisconnect
from loguru import logger
from app.schemas.websocket.websocket_message import WebSocketMessage, WebSocketUserMessage
from app.schemas.main.interview_session import InterviewSession
from app.schemas.main.user_message import UserMessage
from app.services.main_conversation.main_conversation_service import MainConversationService
from app.services.main_conversation.tools.websocket_utils.handle_user_message import handle_user_message
from app.services.transcription.transcriber import TranscriberService
from app.errors.exceptions import InternalServerError

async def handle_websocket_connection(websocket: WebSocket):
    """
    Handle the entire WebSocket conversation lifecycle.
    
    This method manages the WebSocket connection, including:
    - Initial connection setup
    - Message reception and processing
    - Response sending
    - Error handling
    - Connection cleanup
    
    The function establishes the interview session, sends an initial greeting,
    and then enters a continuous loop to handle ongoing conversation messages
    until the connection is closed.
    
    Args:
        websocket (WebSocket): The WebSocket connection object provided by Starlette.
        
    Returns:
        None: This function runs indefinitely until the WebSocket connection is closed.
        
    Raises:
        WebSocketDisconnect: When the client disconnects from the WebSocket.
        InternalServerError: For any other errors during message processing or response generation.
        
    Example:
        This function is typically called by a WebSocket endpoint:
        >>> @app.websocket("/ws")
        >>> async def websocket_endpoint(websocket: WebSocket):
        ...     await websocket.accept()
        ...     await handle_websocket_connection(websocket)
    """
    try:
        # Wait for initial connection message with session details
        initial_message: dict = await websocket.receive_json()
        logger.info(initial_message)
        session = InterviewSession(**initial_message['content'])
        service = MainConversationService()
        # Send initial greeting
        response: str = await service.conversation_with_user_response(session)
        await websocket.send_json(WebSocketMessage(
            type="message",
            content=response
        ).model_dump())

        transcriber = TranscriberService()

        # Handle ongoing conversation
        while True:
            try:
                raw_message: dict = await websocket.receive_json()

                 # Handle heartbeat/ping messages
                if raw_message.get("type") == "ping" or raw_message.get("type") == "heartbeat":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": raw_message.get("timestamp")  # Echo back timestamp if provided
                    })
                    continue

                if raw_message.get("type") == "audio":
                    base64_data = raw_message.get("data")
                    if not base64_data:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing 'data' field for audio"
                        })
                        continue
                    try: 
                        transcript = transcriber.transcribe_base64_audio(base64_data)
                    except Exception as e:
                        logger.error(f"Error transcribing audio: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Error transcribing audio"
                        })
                        continue
                    user_message = UserMessage(
                        session_id=session.session_id,
                        message=transcript
                    )
                    response = await handle_user_message(user_message)
                    await websocket.send_json(WebSocketMessage(
                        type="message",
                        content=response
                    ).model_dump())
                    continue

                # Otherwise, treat as a normal user message (text)
                user_ws_message: WebSocketUserMessage = WebSocketUserMessage.model_validate(raw_message)
                user_message: UserMessage = UserMessage(
                    session_id=session.session_id,
                    message=user_ws_message.content
                )
                response: str = await handle_user_message(user_message)
                await websocket.send_json(WebSocketMessage(
                    type="message",
                    content=response
                ).model_dump())
            except WebSocketDisconnect:
                logger.info("WebSocket connection closed by client")
                break
            except InternalServerError as e:
                logger.error(f"Internal server error in websocket message handling: {e}")
                try:
                    await websocket.send_json(WebSocketMessage(
                        type="error",
                        content=str(e)
                    ).model_dump())
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed while sending error")
                    break
            except Exception as e:
                logger.error(f"Error in websocket message handling: {e}")
                try:
                    await websocket.send_json(WebSocketMessage(
                        type="error",
                        content="An unexpected error occurred in websocket message handling."
                    ).model_dump())
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed while sending error")
                    break
    except WebSocketDisconnect as e:
        logger.info("WebSocket connection closed during initial setup")
    except InternalServerError:
        raise
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
        try:
            await websocket.send_json(WebSocketMessage(
                type="error",
                content="An unexpected error occurred in websocket connection."
            ).model_dump())
        except WebSocketDisconnect:
            logger.info("WebSocket connection closed while sending error")
