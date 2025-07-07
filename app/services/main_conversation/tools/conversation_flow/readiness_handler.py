"""
Readiness Handler Utility Module

This module provides functionality to handle user readiness checks and
interview session initialization. It processes user messages to determine
if they're ready to begin the interview and starts the first question.

Dependencies:
- app.services.main_conversation.tools.question_utils.get_current_question: For fetching current questions.

Author: @kcaparas1630
"""

from typing import Dict, List
from app.services.main_conversation.tools.question_utils.get_current_question import get_current_question


def handle_readiness_check(
    session_id: str, 
    user_message: str, 
    session_state: Dict,
    session_questions: Dict[str, List[str]],
    current_question_index: Dict[str, int],
    add_to_context_func
) -> str:
    """
    Handle user readiness check and start the interview if ready.
    
    Args:
        session_id (str): The session identifier.
        user_message (str): The user's message.
        session_state (Dict): The current session state.
        session_questions (Dict[str, List[str]]): Questions for each session.
        current_question_index (Dict[str, int]): Current question index for each session.
        add_to_context_func: Function to add messages to conversation context.
        
    Returns:
        str: Response message indicating readiness status or first question.
        
    Example:
        >>> session_state = {"123": {"ready": False}}
        >>> response = handle_readiness_check("123", "I'm ready", session_state, ...)
        >>> print(response)  # "Great! I'm excited to see how you do..."
    """
    ready_keywords = ["yes", "ready", "i'm ready", "let's start", "let's go"]
    
    if user_message and any(keyword in user_message.lower() for keyword in ready_keywords):
        session_state["ready"] = True
        session_state["waiting_for_answer"] = True
        current_question = get_current_question(session_id, session_questions, current_question_index)
        response = f"Great! I'm excited to see how you do. Here's your first question {current_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
        add_to_context_func(session_id, "assistant", response)
        return response
    else:
        return "Let me know when you're ready to begin!" 
