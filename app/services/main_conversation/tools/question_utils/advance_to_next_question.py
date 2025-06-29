"""
Question Advancement Utility Module

This module provides functionality to advance through the question sequence in an interview session.
It manages the current question index for each session, allowing the system to progress through
the predefined set of interview questions.

The module contains a single function that increments the question index for a given session,
enabling the interview flow to move from one question to the next.

Dependencies:
- typing: For type annotations.

Author: @kcaparas1630
"""

from typing import Dict

def advance_to_next_question(session_id: str, _current_question_index: Dict[str, int]) -> None:
    """
    Move to the next question in the sequence.
    
    This function increments the current question index for the specified session,
    allowing the interview to progress to the next question in the predefined sequence.
    If the session does not exist in the index, no action is taken.
    
    Args:
        session_id (str): The unique identifier for the interview session.
        _current_question_index (Dict[str, int]): Dictionary mapping session IDs to their current question indices.
        
    Returns:
        None: This function modifies the provided dictionary in-place.
        
    Example:
        >>> _current_question_index = {"session_123": 0}
        >>> advance_to_next_question("session_123", _current_question_index)
        >>> print(_current_question_index["session_123"])  # Output: 1
    """
    if session_id in _current_question_index:
        _current_question_index[session_id] += 1
