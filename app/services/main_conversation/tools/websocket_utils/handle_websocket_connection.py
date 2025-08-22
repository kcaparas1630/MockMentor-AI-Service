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
from app.services.transcription.audio_buffer import IncrementalAudioBuffer
from app.services.facial_landmarks_analysis.facial_landmarks_analysis import facial_landmarks_analyzer
from app.core.ai_client_manager import get_facial_analysis_client
from app.services.main_conversation.tools.unified_feedback import store_facial_analysis_and_check_unified_feedback
import asyncio
from typing import Optional
import time

async def send_websocket_message(websocket: WebSocket, message_type: str, content: str,       
  state: dict = None, next_question: dict = None):
      """Send a WebSocket message with consistent formatting."""
      await websocket.send_json(WebSocketMessage(
          type=message_type,
          content=content,
          state=state,
          next_question=next_question,
          timestamp=str(int(time.time() * 1000))  # Add this line
      ).model_dump())

async def send_error_message(websocket: WebSocket, error_message: str):
    """Send an error message to the WebSocket client."""
    await websocket.send_json({
        "type": "error",
        "content": error_message,
        "timestamp": str(int(time.time() * 1000))
    })

async def safe_transcribe(transcriber: TranscriberService, audio_data: str) -> Optional[str]:
    """
    Safely transcribe audio data with error handling.
    """
    transcription_start = time.time()
    try:
        logger.debug(f"Starting transcription of {len(audio_data)} chars of audio data")
        transcript = transcriber.transcribe_base64_audio(audio_data)
        transcription_time = time.time() - transcription_start
        
        if transcript and transcript.strip():
            logger.debug(f"Transcription completed in {transcription_time:.3f}s, result: {len(transcript)} chars")
            return transcript.strip()
        else:
            logger.debug(f"Transcription completed in {transcription_time:.3f}s, but result was empty")
            return None
    except Exception as e:
        transcription_time = time.time() - transcription_start
        logger.warning(f"Transcription failed after {transcription_time:.3f}s: {e}")
        return None

async def process_transcript(transcript: str, websocket: WebSocket, session: InterviewSession):
    """Process transcribed text and generate AI response."""
    process_start_time = time.time()
    
    try:
        user_message = UserMessage(
            session_id=session.session_id,
            message=transcript
        )
        
        # Send transcript confirmation to client
        transcript_send_start = time.time()
        await websocket.send_json({
            "type": "transcript",
            "content": transcript,
            "timestamp": str(int(time.time() * 1000))  # Add this line
        })
        transcript_send_time = time.time() - transcript_send_start
        logger.debug(f"Sent transcript to client in {transcript_send_time:.3f}s")
        
        # Process AI response
        ai_processing_start = time.time()
        response, session_state = await handle_user_message(user_message)
        ai_processing_time = time.time() - ai_processing_start
        logger.debug(f"AI processing completed in {ai_processing_time:.3f}s")
        
        # Send AI response
        response_send_start = time.time()
        await send_response(websocket, response, session_state)
        response_send_time = time.time() - response_send_start
        logger.debug(f"Sent AI response to client in {response_send_time:.3f}s")
        
        total_process_time = time.time() - process_start_time
        logger.info(f"Complete transcript processing took {total_process_time:.3f}s (transcript: {transcript_send_time:.3f}s, AI: {ai_processing_time:.3f}s, response: {response_send_time:.3f}s)")
        
    except Exception as e:
        logger.error(f"Error processing transcript: {e}")
        await send_error_message(websocket, "Error processing transcript")
async def send_response(websocket: WebSocket, response: str, session_state: dict = None):
    """Send AI response and handle session end if needed."""
    try:
        if response.startswith("NEXT_QUESTION:"):
            # Parse and send structured next question data
            import json
            try: 
                data_json = response[14:]  # Remove "NEXT_QUESTION:" prefix
                response_data = json.loads(data_json)
                logger.debug(f"Parsed NEXT_QUESTION data: {response_data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse NEXT_QUESTION data: {e}")
                await send_error_message(websocket, "Invalid NEXT_QUESTION data format")
                return
            
            # Send single message with feedback and next question data combined
            next_question_data = {
                "question": response_data["next_question"]["question"],
                "questionNumber": response_data["next_question"]["questionNumber"],
                "totalQuestions": response_data["next_question"]["totalQuestions"],
                "questionIndex": response_data["next_question"]["questionIndex"]
            }
            # Get message content from response data which is the merged feedback from the evaluation summary
            message_content = response_data.get("merged_feedback", "")
            
            # Create response with question progression data only
            comprehensive_response = {
                "type": "next_question",
                "content": f"{message_content}",
                "state": session_state,
                "next_question": next_question_data,
                "timestamp": str(int(time.time() * 1000))
            }
            
            await websocket.send_json(comprehensive_response)
        elif response.startswith("INTERVIEW_COMPLETE:"):
            # Parse and send interview completion data
            import json
            try:
                data_json = response[19:]  # Remove "INTERVIEW_COMPLETE:" prefix
                response_data = json.loads(data_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse INTERVIEW_COMPLETE data: {e}")
                await send_error_message(websocket, "Invalid INTERVIEW_COMPLETE data format")
                return
            
            # TODO: REMOVE - This sends text analysis feedback in interview completion to WebSocket client
            # Should be replaced with unified feedback logic using stored session analysis
            await websocket.send_json({
                "type": "interview_complete",
                "content": response_data["feedback"],
                "message": response_data["message"],
                "state": session_state,
                "timestamp": str(int(time.time() * 1000))
            })
        else:
            await send_websocket_message(websocket, "message", response, session_state)
    except Exception as e:
        logger.error(f"Error sending response: {e}")
        raise

async def handle_websocket_connection(websocket: WebSocket):
    """
    Enhanced WebSocket handler with optimized incremental transcription.
    """
    audio_buffer = IncrementalAudioBuffer(
        incremental_size_threshold=5,  # Transcribe every 5 chunks
        final_timeout=2.0  # Wait 2 seconds after last chunk
    )
    transcriber = TranscriberService()
    session: Optional[InterviewSession] = None
    service: Optional[MainConversationService] = None
    
    # Track the last sent incremental transcript to avoid duplicates
    last_incremental_transcript: str = ""
    
    # Configuration for transcription strategy
    use_overlapping_transcription = True  # Set to False to use new-chunks-only approach
    overlap_chunks = 2  # Number of chunks to overlap for context

    try:
        initial_message: dict = await websocket.receive_json()
        logger.info(f"Received initial message: {initial_message}")
        
        session = InterviewSession(**initial_message['content'])
        service = MainConversationService()
        
        response: str = await service.conversation_with_user_response(session)
        session_state_obj = service._session_state_dict.get_session(session.session_id)
        session_state = session_state_obj.model_dump() if session_state_obj else {}
        await send_websocket_message(websocket, "message", response, session_state)
        
        while True:
            try:
                raw_message: dict = await asyncio.wait_for(
                    websocket.receive_json(), 
                    timeout=30.0
                )
                
                message_type = raw_message.get("type")
                
                if message_type in ["ping", "heartbeat"]:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "content": "pong",
                        "timestamp": str(int(time.time() * 1000))
                    })
                    continue
                
                if message_type == "audio_chunk":
                    chunk_data = raw_message.get("data")
                    is_speaking = raw_message.get("isSpeaking", True)
                    
                    if not chunk_data:
                        await send_error_message(websocket, "Missing 'data' field for audio chunk")
                        continue
                    
                    audio_buffer.add_chunk(chunk_data, is_speaking)
                    
                    # Check if we should do incremental transcription
                    if audio_buffer.should_do_incremental_transcription():
                        transcription_start_time = time.time()
                        
                        # Choose transcription strategy
                        if use_overlapping_transcription:
                            # Use overlapping audio data to avoid missing words at chunk boundaries
                            incremental_audio = audio_buffer.get_overlapping_audio_data(overlap_chunks=overlap_chunks)
                            strategy = "overlapping"
                        else:
                            # Use only new chunks since last transcription
                            incremental_audio = audio_buffer.get_incremental_audio_data()
                            strategy = "new-chunks-only"
                        
                        if incremental_audio:
                            # Calculate how many NEW chunks we're processing
                            new_chunks_count = len(audio_buffer.chunks) - audio_buffer.last_incremental_size
                            logger.debug(f"Attempting {strategy} incremental transcription with {new_chunks_count} new chunks (total: {len(audio_buffer.chunks)})")
                            
                            # Try to transcribe the new audio
                            transcript = await safe_transcribe(transcriber, incremental_audio)
                            
                            transcription_time = time.time() - transcription_start_time
                            
                            if transcript and transcript != last_incremental_transcript:
                                await send_websocket_message(websocket, "incremental_transcript", transcript)
                                last_incremental_transcript = transcript
                                logger.debug(f"Sent incremental transcript ({strategy}, {transcription_time:.2f}s): {transcript[:50]}...")
                            else:
                                logger.debug(f"Skipped duplicate/empty transcript ({strategy}, {transcription_time:.2f}s)")
                            
                            # Mark that we've done incremental transcription
                            audio_buffer.mark_incremental_transcription_done()
                    
                    continue
                
                if message_type == "audio_end":
                    logger.info("Received audio_end signal from client.")
                    
                    # Process audio_end in background to not block other messages
                    async def process_audio_end():
                        audio_end_start = time.time()
                        
                        # Force final transcription if we have any remaining chunks
                        if audio_buffer.has_chunks():
                            final_audio_prep_start = time.time()
                            final_audio = audio_buffer.get_final_audio_data()
                            final_audio_prep_time = time.time() - final_audio_prep_start
                            logger.debug(f"Final audio preparation took {final_audio_prep_time:.3f}s")
                            
                            if final_audio:
                                logger.debug(f"Processing final transcription with {len(audio_buffer.chunks)} chunks, audio size: {len(final_audio)} chars")
                                
                                final_transcription_start = time.time()
                                transcript = await safe_transcribe(transcriber, final_audio)
                                final_transcription_time = time.time() - final_transcription_start
                                logger.debug(f"Final transcription took {final_transcription_time:.3f}s")
                                
                                if transcript:
                                    logger.info(f"Final transcript ({len(transcript)} chars): {transcript}")
                                    
                                    # Process the transcript (send to client + AI processing)
                                    await process_transcript(transcript, websocket, session)
                                else:
                                    logger.warning("Final transcription failed or returned empty result")
                        
                        # Clear the buffer and reset state
                        audio_buffer.clear()
                        nonlocal last_incremental_transcript
                        last_incremental_transcript = ""
                        
                        total_audio_end_time = time.time() - audio_end_start
                        logger.info(f"Complete audio_end processing took {total_audio_end_time:.3f}s")
                    
                    # Run audio processing in background with error handling
                    async def process_audio_end_with_error_handling():
                        try:
                            await process_audio_end()
                        except Exception as e:
                            logger.error(f"Error in background audio processing: {e}")
                            import traceback
                            logger.error(f"Full traceback: {traceback.format_exc()}")
                            # Optionally notify client of processing error
                            try:
                                await send_error_message(websocket, "Audio processing failed")
                            except:
                                pass  # WebSocket might be closed
                    
                    task = asyncio.create_task(
                        process_audio_end_with_error_handling(),
                        name=f"audio_end_processing_{session.session_id if session else 'unknown'}"
                    )
                    logger.debug(f"Created background task: {task.get_name()}")
                    continue

                if message_type == "emotion_features":
                    logger.info("Received emotion features request from client.")
                    logger.debug(f"Emotion features data: {raw_message}")
                    
                    # Extract emotion features data from the message
                    emotion_data = raw_message.get("data", {})
                    
                    # Validate emotion features data
                    if not emotion_data:
                        logger.warning("Empty emotion data received")
                        await send_error_message(websocket, "No emotion data provided for emotion analysis")
                        continue
                    
                    logger.debug(f"Received emotion features: {emotion_data}")
                    
                    # Validate emotion features structure
                    required_fields = ["smile", "eyeOpen", "browRaise", "mouthOpen", "tension", "symmetry", "confidence", "timestamp", "frameId"]
                    if not all(key in emotion_data for key in required_fields):
                        logger.warning("Invalid emotion data structure")
                        await send_error_message(websocket, "Invalid emotion data format - missing required fields")
                        continue
                    
                    # Check if user is ready for interview before performing facial analysis
                    current_session_state = service._session_state_dict.get_session(session.session_id)
                    if not current_session_state or not current_session_state.ready:
                        logger.info(f"Skipping emotion analysis for session {session.session_id} - user not ready for interview")
                        continue
                    
                    try:
                        # Use dedicated facial analysis client for better performance
                        facial_analysis_client = get_facial_analysis_client()
                        analysis_result = await facial_landmarks_analyzer.analyze_emotion_features(
                            emotion_data,
                            facial_analysis_client
                        )
                        
                        # Store facial analysis result - unified feedback will be generated in action handlers
                        # (reusing current_session_state from readiness check above)
                        await store_facial_analysis_and_check_unified_feedback(
                            current_session_state, session.session_id, analysis_result
                        )
                        logger.info(f"[EMOTION_ANALYSIS] Stored emotion analysis result for session {session.session_id}")
                        
                    except Exception as e:
                        logger.error(f"Error in emotion analysis: {e}")
                        await send_error_message(websocket, "Failed to process emotion analysis")
                    
                    continue
                
                # Handle legacy full audio blob (for backward compatibility)
                if message_type == "audio":
                    base64_data = raw_message.get("data")
                    if not base64_data:
                        await send_error_message(websocket, "Missing 'data' field for audio")
                        continue
                    
                    transcript = await safe_transcribe(transcriber, base64_data)
                    if transcript:
                        await process_transcript(transcript, websocket, session)
                    continue
                
                if message_type == "message":
                    user_ws_message = WebSocketUserMessage.model_validate(raw_message)
                    user_message = UserMessage(
                        session_id=session.session_id,
                        message=user_ws_message.content
                    )
                    
                    response, session_state = await handle_user_message(user_message)
                    await send_response(websocket, response, session_state)
                    continue
                
                logger.warning(f"Unknown message type: {message_type}")
                await send_error_message(websocket, f"Unknown message type: {message_type}")
                
            except asyncio.TimeoutError:
                timeout_start = time.time()
                logger.debug("WebSocket timeout occurred, checking for final transcription")
                
                # Check if we should do final transcription due to timeout
                if audio_buffer.should_do_final_transcription():
                    final_audio = audio_buffer.get_final_audio_data()
                    if final_audio:
                        logger.debug(f"Timeout: Processing final transcription with {len(audio_buffer.chunks)} chunks")
                        
                        timeout_transcription_start = time.time()
                        transcript = await safe_transcribe(transcriber, final_audio)
                        timeout_transcription_time = time.time() - timeout_transcription_start
                        logger.debug(f"Timeout transcription took {timeout_transcription_time:.3f}s")
                        
                        if transcript:
                            await process_transcript(transcript, websocket, session)
                        
                        audio_buffer.clear()
                        last_incremental_transcript = ""
                
                timeout_total_time = time.time() - timeout_start
                logger.debug(f"Timeout handling completed in {timeout_total_time:.3f}s")
                continue
                
            except WebSocketDisconnect:
                logger.info("WebSocket connection closed by client")
                break
                
            except InternalServerError as e:
                logger.error(f"Internal server error in websocket message handling: {e}")
                try:
                    await send_websocket_message(websocket, "error", str(e))
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed while sending error")
                    break
                    
            except Exception as e:
                logger.error(f"Error in websocket message handling: {e}")
                try:
                    await send_websocket_message(websocket, "error", "An unexpected error occurred")
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed while sending error")
                    break
                    
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed during initial setup")
        # Process any remaining chunks before closing
        if audio_buffer.has_chunks():
            try: 
                final_audio = audio_buffer.get_final_audio_data()
                if final_audio:
                    logger.info("Processing remaining chunks before closing due to disconnect")
                    transcript = await safe_transcribe(transcriber, final_audio)
                    if transcript:
                        # Can't send to closed websocket, but we could log or save it
                        logger.info(f"Final transcript (connection closed): {transcript}")
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup on disconnect: {cleanup_error}")
        
    except InternalServerError:
        raise
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
        try:
            await send_websocket_message(websocket, "error", "An unexpected error occurred in websocket connection")
        except WebSocketDisconnect:
            logger.info("WebSocket connection closed while sending error")
