"""
Session Validator Utility Module

This module provides functionality to validate session state and existence
in interview conversations. It ensures sessions are properly initialized
before processing user messages.

Dependencies:
- app.errors.exceptions: For custom exception handling.

Author: @kcaparas1630
"""

from typing import Dict
from app.errors.exceptions import NotFound


def validate_session_exists(session_id: str, session_state: Dict[str, Dict]) -> None:
    """
    Validate that the session exists and is properly initialized.
    
    Args:
        session_id (str): The session identifier to validate.
        session_state (Dict[str, Dict]): The current session state dictionary.
        
    Raises:
        NotFound: If the session is not found in the session state.
        
    Example:
        >>> session_state = {"123": {"ready": True}}
        >>> validate_session_exists("123", session_state)  # No exception
        >>> validate_session_exists("456", session_state)  # Raises NotFound
    """
    if session_id not in session_state:
        raise NotFound(f"Session {session_id} not found. Session must be initialized first.") 
