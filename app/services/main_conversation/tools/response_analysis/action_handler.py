"""
Action Handler Utility Module

This module provides functionality to handle different types of actions based on
analysis responses. It routes to appropriate handlers for retry, exit,
and continue actions.

Dependencies:
- app.services.main_conversation.tools.response_analysis.action_handlers: For specific action handlers.

Author: @kcaparas1630
"""

from typing import Dict
from loguru import logger
from .action_handlers import (
    handle_retry_action,
    handle_continue_action
)
from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse


async def handle_next_action(
    session_id: str,
    analysis_response: InterviewFeedbackResponse,
    feedback_text: str,
    session_state: Dict,
    session_questions: Dict[str, list],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """
    Handle the next action based on the analysis response.
    
    Args:
        session_id (str): The session identifier.
        analysis_response: The response from TextAnswersService.
        feedback_text (str): The formatted feedback text.
        session_state (Dict): The current session state.
        session_questions (Dict[str, list]): Questions for each session.
        current_question_index (Dict[str, int]): Current question index for each session.
        add_to_context_func: Function to add messages to conversation context.
        advance_to_next_question_func: Function to advance to next question.
        get_current_question_func: Function to get current question.
        reset_question_attempts_func: Function to reset question attempts.
        
    Returns:
        str: The complete response including feedback and next action.
        
    Example:
        >>> response = await handle_next_action("123", analysis_response, feedback, ...)
        >>> print(response)  # Complete response with feedback and next action
    """
    # Add logging to see what action type we get
    logger.info(f"[ACTION_DEBUG] Session {session_id}: action_type='{analysis_response.next_action.type}', message='{analysis_response.next_action.message}'")
    
    # Handle technical issues or retry
    if (analysis_response.technical_issue_detected or analysis_response.needs_retry):
        logger.info("Detected technical issue or retry needed.")
        return await handle_retry_action(
            session_id, analysis_response, feedback_text, session_state,
            session_questions, current_question_index, add_to_context_func,
            advance_to_next_question_func, get_current_question_func, reset_question_attempts_func
        )
    
    # Handle retry question (replaces follow-up logic)
    if analysis_response.next_action.type == "retry_question":
        logger.info("Retry question action detected.")
        return await handle_retry_action(
            session_id, analysis_response, feedback_text, session_state,
            session_questions, current_question_index, add_to_context_func,
            advance_to_next_question_func, get_current_question_func, reset_question_attempts_func
        )
    
    
    # Handle continue (advance to next question)
    if analysis_response.next_action.type == "continue":
        logger.info("Continue action detected, advancing to next question.")
        return await handle_continue_action(
            session_id, analysis_response, feedback_text, session_state,
            session_questions, current_question_index, add_to_context_func,
            advance_to_next_question_func, get_current_question_func, reset_question_attempts_func
        )
    
    # Default case - log when we hit this
    logger.warning(f"[ACTION_DEBUG] Session {session_id}: Falling through to default case! Action type '{analysis_response.next_action.type}' not handled.")
    return feedback_text 
