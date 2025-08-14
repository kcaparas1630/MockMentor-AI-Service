"""
Answer Processor Utility Module

This module provides functionality to process user answers to interview questions,
including analysis, feedback generation, and action handling. It coordinates
the complete flow from user input to AI response.

Dependencies:
- app.services.speech_to_text.text_answers_service: For analyzing user responses.
- app.schemas.session_evaluation_schemas.interview_analysis_request: For analysis request models.
- app.services.main_conversation.tools.question_utils.get_current_question: For fetching current questions.
- app.errors.exceptions: For custom exception handling.

Author: @kcaparas1630
"""

from typing import Dict, List
from app.services.speech_to_text.text_answers_service import TextAnswersService
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.schemas.session_evaluation_schemas import SessionState
from app.services.main_conversation.tools.question_utils.get_current_question import get_current_question
from app.services.main_conversation.tools.question_utils.save_answer import save_answer
from app.errors.exceptions import BadRequest
from loguru import logger


async def process_user_answer(
    session_id: str,
    user_message: str,
    session_state: SessionState,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    client,
    add_to_context_func,
    format_feedback_func,
    handle_next_action_func,
    session_question_data: Dict[str, List[Dict]] = None
) -> str:
    """
    Process user's answer to the current question and generate appropriate response.
    
    Args:
        session_id (str): The session identifier.
        user_message (str): The user's answer.
        session_state (Dict): The current session state.
        session_questions (Dict[str, List[str]]): Questions for each session.
        current_question_index (Dict[str, int]): Current question index for each session.
        client: The OpenAI client for AI interactions.
        add_to_context_func: Function to add messages to conversation context.
        format_feedback_func: Function to format feedback responses.
        handle_next_action_func: Function to handle next actions.
        
    Returns:
        str: The complete response including feedback and next action.
        
    Raises:
        BadRequest: If session metadata is missing.
        
    Example:
        >>> response = await process_user_answer("123", "My answer...", session_state, ...)
        >>> print(response)  # Formatted feedback and next action
    """
    
    
    # Validate session metadata
    if "session_metadata" not in session_state:
        raise BadRequest(f"Session {session_id} metadata not found. Session must be properly initialized.")
    
    # Get current question and session metadata
    current_question = get_current_question(session_id, session_questions, current_question_index)
    current_index = current_question_index.get(session_id, 0)
    session_metadata = session_state.session_metadata
    
    # Analyze the user's response
    logger.info(f"[FLOW_DEBUG] About to call analyze_user_response() for session {session_id}")
    analysis_response = await analyze_user_response(
        session_id, user_message, session_state, session_questions, current_question_index, client
    )
    
    # Store text analysis result in session state for coordination
    session_state.set_text_analysis(analysis_response)
    logger.info(f"[SESSION_STATE] Stored text analysis result for session {session_id}")
    
    # Generate feedback text
    # TODO: REMOVE - This formats and sends text analysis response directly to client
    # Should be replaced with unified feedback logic using stored session analysis
    feedback_text = format_feedback_func(analysis_response)
    add_to_context_func(session_id, "assistant", feedback_text)
    
    # Save answer with feedback data to MongoDB
    feedback_data = {
        "score": analysis_response.score,
        "tips": analysis_response.tips,
        "feedback": feedback_text
    }
    
    save_result = await save_answer(
        session_id=session_id,
        question=current_question,
        answer=user_message,
        question_index=current_index,
        metadata={
            "jobRole": session_metadata.jobRole,
            "jobLevel": session_metadata.jobLevel, 
            "questionType": session_metadata.questionType
        },
        feedback_data=feedback_data,
        session_question_data=session_question_data
    )
    
    if save_result["success"]:
        logger.info(f"Successfully saved answer with feedback for session {session_id}, question {current_index}")
    else:
        logger.error(f"Failed to save answer with feedback: {save_result['error']}")
    
    # Handle the next action based on analysis
    # TODO: REMOVE - This passes text analysis response and feedback to action handler for immediate client sending
    # Should be replaced with unified feedback logic using stored session analysis
    return await handle_next_action_func(session_id, analysis_response, feedback_text, session_state)


async def analyze_user_response(
    session_id: str,
    user_message: str,
    session_state: SessionState,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    client
):
    """
    Analyze the user's response using the TextAnswersService.
    
    Args:
        session_id (str): The session identifier.
        user_message (str): The user's answer.
        session_state (Dict): The current session state.
        session_questions (Dict[str, List[str]]): Questions for each session.
        current_question_index (Dict[str, int]): Current question index for each session.
        client: The OpenAI client for AI interactions.
        
    Returns:
        Analysis response from TextAnswersService.
    """
    session_metadata = session_state.session_metadata
    current_question = get_current_question(session_id, session_questions, current_question_index)
    
    analysis_request = InterviewAnalysisRequest(
        session_metadata=session_metadata,
        interviewType=session_metadata.questionType,
        question=current_question,
        answer=user_message
    )
    
    # Use the provided client (should be text analysis client from caller)
    logger.debug("Using provided text analysis client for response feedback")
    text_answers_service = TextAnswersService(client)
    result = await text_answers_service.analyze_response(analysis_request)
    return result 
