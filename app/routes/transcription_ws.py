"""
Description:
WebSocket route for AI Coach Transcription
This route handles real-time audio transcription via WebSocket.
It accepts audio data in base64 format and returns the transcribed text.

Arguments:
- websocket: WebSocket connection object

Returns:
- JSON response with the type "transcript" and the transcribed text,
  or an error message if the input is invalid or processing fails.

Dependencies:
- fastapi: For creating the FastAPI application and handling WebSocket connections.
- app.services.transcription.transcriber: For transcribing base64 audio data.
- loguru: For logging information about the WebSocket connection and any exceptions that occur.

Authors: @kcaparas1630
        @William226

"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.transcription.transcriber import transcribe_base64_audio
from loguru import logger

router = APIRouter(
    prefix="/api",
    tags=["ai-coach-transcription"],
    responses={404: {"description": "Not found"}}
)

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
                    "content": transcript
                })

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Processing error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "An error occurred while processing the audio"
                    })
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected during error handling")
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {e}")
