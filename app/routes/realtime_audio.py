from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.transcription.transcriber import TranscriberService
from collections import deque
import time
import asyncio

router = APIRouter()

# Helper class to buffer audio chunks
class AudioStreamBuffer:
    def __init__(self, max_buffer_size=5, chunk_timeout=3.0):
        self.buffer = deque()
        self.max_buffer_size = max_buffer_size
        self.chunk_timeout = chunk_timeout
        self.last_chunk_time = None

    def add_chunk(self, chunk):
        self.buffer.append(chunk)
        self.last_chunk_time = time.time()

    def should_transcribe(self):
        if len(self.buffer) >= self.max_buffer_size:
            return True
        if self.last_chunk_time and (time.time() - self.last_chunk_time) >= 0.5:
            return True
        return False

    def get_and_clear(self):
        chunks = list(self.buffer)
        self.buffer.clear()
        return chunks

    def is_empty(self):
        return len(self.buffer) == 0

    def is_timed_out(self):
        return self.last_chunk_time and (time.time() - self.last_chunk_time) >= self.chunk_timeout


@router.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket):
    await websocket.accept()
    buffer = AudioStreamBuffer()
    transcriber = TranscriberService()

    async def try_transcribe():
        """ Transcribe and send result back if buffer has content """
        if not buffer.is_empty():
            combined = "".join(buffer.get_and_clear())
            try:
                transcript = transcriber.transcribe_base64_audio(combined)
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=buffer.chunk_timeout)
            except asyncio.TimeoutError:
                if buffer.is_timed_out():
                    await try_transcribe()
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "audio_chunk":
                # Base64 chunk from frontend VAD
                chunk = msg.get("chunk")
                if chunk:
                    buffer.add_chunk(chunk)
                if buffer.should_transcribe():
                    await try_transcribe()

            elif msg_type == "audio_end":
                # Mark stream end, flush remaining buffer
                await try_transcribe()
                break

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})