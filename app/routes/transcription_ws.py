from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.transcription.transcriber import transcribe_base64_audio
from loguru import logger

router = APIRouter()

# What This Does: 
# - Accepts connections to /ws/transcription
# - Listens for messages of the form:
#   - { "type": "audio", "data": "BASE64_ENCODED_AUDIO" }
# - Transcribes the audio and sends back:
#   - { "type": "transcript", "text": "..." }

@router.websocket("/ws/transcription")
async def transcription_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected for transcription")

    try:
        while True:
            try:
                message = await websocket.receive_json()

                if message.get("type") != "audio":
                    await websocket.send_json({
                        "type": "error",
                        "message": "Unsupported message type"
                    })
                    continue

                base64_data = message.get("data")
                if not base64_data:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing 'data' field"
                    })
                    continue

                transcript = transcribe_base64_audio(base64_data)
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript
                })

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Processing error: {str(e)}"
                    })
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected during error handling")
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {e}")
