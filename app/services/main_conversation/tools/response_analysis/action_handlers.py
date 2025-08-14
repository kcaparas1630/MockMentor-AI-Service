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
import json
from app.schemas.session_evaluation_schemas import SessionState

async def handle_retry_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: SessionState,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func
) -> str:
    """Handle retry actions when technical issues are detected."""
    logger.debug(f"[RETRY] Session {session_id}: retry_attempts={session_state.get('retry_attempts', 0)}")
    
    if session_state.retry_attempts < 1:
        session_state.retry_attempts += 1
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
            reset_question_attempts_func,
            analysis_response
        )

async def handle_continue_action(
    session_id: str,
    analysis_response,
    feedback_text: str,
    session_state: SessionState,
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
        current_index = current_question_index[session_id]
        total_questions = len(session_questions[session_id])
        
        next_message = f"Here's your next question: {next_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
        add_to_context_func(session_id, "assistant", next_message)
        session_state.waiting_for_answer = True
        reset_question_attempts_func(session_state)
        
        # Return structured response with next question data
        # TODO: REMOVE - This builds response data with text analysis feedback for immediate client sending
        # Should be replaced with unified feedback logic using stored session analysis
        response_data = {
            "type": "next_question",
            "feedback_formatted": feedback_text,
            "next_action_message": analysis_response.next_action.message,
            "next_question": {
                "question": next_question,
                "questionNumber": current_index + 1,
                "totalQuestions": total_questions,
                "questionIndex": current_index
            },
            "message": next_message
        }
        
        return f"NEXT_QUESTION:{json.dumps(response_data)}"
    else:
        session_state.waiting_for_answer = False
        end_message = "That's the end of the interview. Great job!"
        add_to_context_func(session_id, "assistant", end_message)
        logger.info(f"Feedback and end message: {feedback_text + end_message}")
        
        # Return structured response for interview completion
        response_data = {
            "type": "interview_complete",
            "feedback": feedback_text + end_message,
            "message": end_message
        }
        
        return f"INTERVIEW_COMPLETE:{json.dumps(response_data)}"


async def advance_to_next_question_with_message(
    session_id: str,
    feedback_text: str,
    session_state: SessionState,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func,
    advance_to_next_question_func,
    get_current_question_func,
    reset_question_attempts_func,
    analysis_response=None
) -> str:
    """Helper method to advance to next question with a custom prefix message."""
    advance_to_next_question_func(session_id, current_question_index)
    
    if current_question_index[session_id] < len(session_questions[session_id]):
        next_question = get_current_question_func(session_id, session_questions, current_question_index)
        next_message = f" {next_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
        current_index = current_question_index[session_id]
        total_questions = len(session_questions[session_id])
        add_to_context_func(session_id, "assistant", next_message)
        session_state.waiting_for_answer = True
        reset_question_attempts_func(session_state)
        logger.info(f"Feedback and next question message: {feedback_text + next_message}")
        
        # Return structured response with next question data
        # TODO: REMOVE - This builds retry response data with text analysis feedback for immediate client sending
        # Should be replaced with unified feedback logic using stored session analysis
        response_data = {
            "type": "next_question",
            "feedback_formatted": feedback_text,
            "next_action_message": analysis_response.next_action.message if analysis_response else "",
            "next_question": {
                "question": next_question,
                "questionNumber": current_index + 1,
                "totalQuestions": total_questions,
                "questionIndex": current_index
            },
            "message": next_message
        }
        return f"NEXT_QUESTION:{json.dumps(response_data)}"
    # If no more questions, end the interview
    else:
        session_state.waiting_for_answer = False
        end_message = "That's the end of the interview. Great job!"
        add_to_context_func(session_id, "assistant", end_message)
        # Return structured response for interview completion
        response_data = {
            "type": "interview_complete",
            "feedback": feedback_text + end_message,
            "message": end_message
        }
        return f"INTERVIEW_COMPLETE:{json.dumps(response_data)}"

def reset_question_attempts(session_state: SessionState) -> None:
    """Reset retry attempts for a new question."""
    session_state.retry_attempts = 0
