from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.main_conversation_service import MainConversationService
from loguru import logger


router = APIRouter(
    prefix="/api",
    tags=["ai-coach-conversation"]
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
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)
