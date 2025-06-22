from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.main_conversation_service import MainConversationService
from loguru import logger


router = APIRouter(
    prefix="/api",
    tags=["ai-coach-conversation"],
    responses={404: {"description": "Not found"}}
)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    service = MainConversationService()
    try:
        await service.handle_websocket_connection(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.exception("Unhandled exception in websocket connection")
        #1011 = internal error
        await websocket.close(code=1011, reason=str(e)[:123])
        raise # re-raise the exception to be handled by the FastAPI error handler
