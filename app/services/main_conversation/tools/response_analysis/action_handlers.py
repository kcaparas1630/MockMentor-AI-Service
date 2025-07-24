"""
Action Handlers Utility Module

This module provides specific handlers for different types of actions in interview
conversations: retry, follow-up, exit, and continue actions. Each handler manages
the specific logic for its action type.

Dependencies:
- app.services.main_conversation.tools.question_utils.advance_to_next_question: For advancing questions.

Author: @kcaparas1630
"""

from typing import Dict, List
from loguru import logger

async def handle_retry_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: Dict,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """Handle retry actions when technical issues are detected."""
    if session_state["retry_attempts"] < 1:
        session_state["retry_attempts"] += 1
        retry_message = analysis_response.next_action.message
        add_to_context_func(session_id, "assistant", retry_message)
        logger.info(f"Feedback and retry message: {feedback_text + retry_message}")
        return feedback_text + retry_message
    else:
        # Max retries reached, move to next question
        return await advance_to_next_question_with_message(
            session_id,
            feedback_text + "Due to technical difficulties, let's move on to the next question. ",
            session_state,
            session_questions,
            current_question_index,
            add_to_context_func,
            advance_to_next_question_func,
            get_current_question_func,
            reset_question_attempts_func
        )


async def handle_follow_up_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: Dict,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """Handle follow-up actions when engagement check is needed."""
    if session_state["follow_up_attempts"] < 1:
        session_state["follow_up_attempts"] += 1
        follow_up_message = analysis_response.next_action.message
        
        # Optionally include follow-up details if present
        if analysis_response.next_action.follow_up_question_details:
            details = analysis_response.next_action.follow_up_question_details
            follow_up_message += f" {details.original_question}"
        
        add_to_context_func(session_id, "assistant", follow_up_message)
        logger.info(f"Feedback and follow-up message: {feedback_text + follow_up_message}")
        return feedback_text + follow_up_message
    else:
        # Max follow-ups reached, move to next question
        return await advance_to_next_question_with_message(
            session_id,
            feedback_text + "Let's move on to the next question. ",
            session_state,
            session_questions,
            current_question_index,
            add_to_context_func,
            advance_to_next_question_func,
            get_current_question_func,
            reset_question_attempts_func
        )


async def handle_exit_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: Dict,
    add_to_context_func
) -> str:
    """Handle exit actions when the interview should end."""
    exit_message = analysis_response.next_action.message
    add_to_context_func(session_id, "assistant", exit_message)
    session_state["waiting_for_answer"] = False
    logger.info(f"Feedback and exit message: {feedback_text + exit_message}")
    # Return a special marker to indicate session should end
    return "SESSION_END:" + feedback_text + exit_message


async def handle_continue_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: Dict,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """Handle continue actions to advance to the next question."""
    advance_to_next_question_func(session_id, current_question_index)
    
    # Check if more questions remain
    if current_question_index[session_id] < len(session_questions[session_id]):
        next_question = get_current_question_func(session_id, session_questions, current_question_index)
        next_message = f"Here's your next question: {next_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
        add_to_context_func(session_id, "assistant", next_message)
        session_state["waiting_for_answer"] = True
        reset_question_attempts_func(session_state)
        return feedback_text + analysis_response.next_action.message + next_message
    else:
        session_state["waiting_for_answer"] = False
        end_message = analysis_response.next_action.message + "That's the end of the interview. Great job!"
        add_to_context_func(session_id, "assistant", end_message)
        logger.info(f"Feedback and end message: {feedback_text + end_message}")
        return feedback_text + end_message


async def advance_to_next_question_with_message(
    session_id: str,
    prefix_message: str,
    session_state: Dict,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """Helper method to advance to next question with a custom prefix message."""
    advance_to_next_question_func(session_id, current_question_index)
    
    if current_question_index[session_id] < len(session_questions[session_id]):
        next_question = get_current_question_func(session_id, session_questions, current_question_index)
        next_message = f" {next_question} Take your time, and remember to be specific about your role and the impact you made."
        add_to_context_func(session_id, "assistant", next_message)
        session_state["waiting_for_answer"] = True
        reset_question_attempts_func(session_state)
        logger.info(f"Feedback and next question message: {prefix_message + next_message}")
        return prefix_message + next_message
    else:
        session_state["waiting_for_answer"] = False
        end_message = "That's the end of the interview. Great job!"
        add_to_context_func(session_id, "assistant", end_message)
        logger.info(f"Feedback and end message: {prefix_message + end_message}")
        return prefix_message + end_message


def reset_question_attempts(session_state: Dict) -> None:
    """Reset retry and follow-up attempts for a new question."""
    session_state["retry_attempts"] = 0
    session_state["follow_up_attempts"] = 0
    session_state["question_answered"] = False 
