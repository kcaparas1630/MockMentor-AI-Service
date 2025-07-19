"""
System Prompt Generation Utility Module

This module provides functionality to generate system prompts for the AI interviewer based on
interview session details. It creates comprehensive, context-aware prompts that guide the AI's
behavior during interview sessions.

The module contains a single function that constructs a detailed system prompt incorporating
the session's job role, level, and question type, along with specific instructions for
maintaining a supportive interview environment.

Dependencies:
- app.schemas.main.interview_session: For interview session data models.

Author: @kcaparas1630
"""

from app.schemas.main.interview_session import InterviewSession
from app.core.secure_prompt_manager import secure_prompt_manager

def get_system_prompt(interview_session: InterviewSession) -> str:
    """
    Generate the system prompt for the AI based on the interview session details.

    This function creates a comprehensive system prompt that defines the AI's role,
    behavior guidelines, and conversation flow for the interview session. The prompt
    includes specific instructions for question handling, conversation management,
    and maintaining a supportive interview environment.

    Args:
        interview_session (InterviewSession): The interview session object containing
            job details (user_name, jobRole, jobLevel, questionType) and session identifier.

    Returns:
        str: A comprehensive system prompt that guides the AI's behavior during the interview.

    Example:
        >>> session = InterviewSession(session_id="123", user_name="John", 
        ...                           jobRole="Software Engineer", jobLevel="Mid", 
        ...                           questionType="Behavioral")
        >>> prompt = get_system_prompt(session)
        >>> print("Hi John" in prompt)  # True
    """
    return secure_prompt_manager.get_system_prompt(interview_session)
