"""
Current Question Retrieval Utility Module

This module provides functionality to retrieve the current question for an interview session.
It manages access to the question sequence and handles edge cases such as session completion
or missing session data.

The module contains a single function that returns the current question based on the session's
question index, or a completion message if all questions have been answered.

Dependencies:
- typing: For type annotations.

Author: @kcaparas1630
"""

from typing import Dict, List

def get_current_question(session_id: str, _session_questions: Dict[str, List[str]], _current_question_index: Dict[str, int]) -> str:
    """
    Get the current question for the session.
    
    This function retrieves the current question based on the session's question index.
    It handles various scenarios including session completion and missing session data.
    
    Args:
        session_id (str): The unique identifier for the interview session.
        _session_questions (Dict[str, List[str]]): Dictionary mapping session IDs to their question lists.
        _current_question_index (Dict[str, int]): Dictionary mapping session IDs to their current question indices.
        
    Returns:
        str: The current question for the session, or a completion message if all questions are done.
        
    Raises:
        Exception: If no questions are found for the specified session.
        
    Example:
        >>> _session_questions = {"session_123": ["Question 1", "Question 2"]}
        >>> _current_question_index = {"session_123": 0}
        >>> get_current_question("session_123", _session_questions, _current_question_index)
        "Question 1"
    """
    if session_id not in _session_questions:
        raise Exception("No questions found for session")
    
    questions = _session_questions[session_id]
    current_index = _current_question_index.get(session_id, 0)
    
    if current_index >= len(questions):
        return "We've completed all the questions for this interview session."
    
    return questions[current_index]
