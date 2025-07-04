"""
WebSocket route for AI Coach Conversation

Description:
This module defines a FastAPI route for handling WebSocket connections for AI Coach conversations.
It accepts WebSocket connections and processes messages using the MainConversationService.

Arguments:
- websocket: WebSocket connection object

Returns:
- None, but handles incoming messages and sends responses through the WebSocket connection.

Dependencies:
- fastapi: For creating the FastAPI application and handling WebSocket connections.
- app.services.main_conversation.tools.websocket_utils.handle_websocket_connection: For processing conversation logic.
- loguru: For logging information about the WebSocket connection and any exceptions that occur.
Author: @kcaparas1630

"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.main_conversation.tools.websocket_utils.handle_websocket_connection import handle_websocket_connection
from loguru import logger

router = APIRouter(
    prefix="/api",
    tags=["ai-coach-conversation"],
    responses={404: {"description": "Not found"}}
)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Wait for initial connection message with session details
        # The handler will receive the initial message itself
        await handle_websocket_connection(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.exception("Unhandled exception in websocket connection")
        #1011 = internal error
        await websocket.close(code=1011, reason=str(e)[:123])
        raise # re-raise the exception to be handled by the FastAPI error handler
