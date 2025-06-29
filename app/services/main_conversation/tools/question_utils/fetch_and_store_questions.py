"""
Question Fetching and Storage Utility Module

This module provides functionality to fetch interview questions from the database and store them
for use in an interview session. It acts as a bridge between the database layer and the main
conversation service, ensuring questions are properly retrieved and cached for the session.

The module contains a single async function that handles the complete workflow of fetching
questions based on job criteria and storing them in the session's question cache.

Dependencies:
- app.schemas.main.interview_session: For interview session data models.
- .get_questions: For database question retrieval.
- loguru: For logging operations.

Author: @kcaparas1630
"""

from .....schemas.main.interview_session import InterviewSession
from .get_questions import get_questions
from loguru import logger

async def fetch_and_store_questions(interview_session: InterviewSession, _session_questions: dict, _current_question_index: dict) -> list:
    """
    Fetch questions from database and store them for the session.
    
    This function retrieves interview questions from the database based on the session's
    job criteria (role, level, and question type) and stores them in the session's
    question cache. It also initializes the question index for the session.
    
    Args:
        interview_session (InterviewSession): The interview session object containing job details
            (jobRole, jobLevel, questionType) and session identifier.
        _session_questions (dict): Dictionary to store questions for each session, modified in-place.
        _current_question_index (dict): Dictionary to store current question indices for each session,
            modified in-place.
            
    Returns:
        List[str]: The list of questions fetched and stored for the session.
        
    Raises:
        Exception: If questions cannot be fetched from the database or if no questions
            are found for the specified criteria.
            
    Example:
        >>> session = InterviewSession(session_id="123", jobRole="Software Engineer", 
        ...                           jobLevel="Mid", questionType="Behavioral")
        >>> _session_questions = {}
        >>> _current_question_index = {}
        >>> questions = await fetch_and_store_questions(session, _session_questions, _current_question_index)
        >>> print(len(questions))  # Number of questions fetched
        >>> print(_current_question_index["123"])  # Should be 0 (initialized)
    """
    try:
        questions_result = await get_questions(
            jobRole=interview_session.jobRole,
            jobLevel=interview_session.jobLevel,
            questionType=interview_session.questionType
        )
        
        if not questions_result["success"]:
            raise Exception(f"Failed to fetch questions: {questions_result['error']}")
        
        if questions_result["count"] == 0:
            raise Exception(f"No questions found for {interview_session.jobRole} {interview_session.jobLevel} {interview_session.questionType}")
        
        # Store questions and initialize index
        _session_questions[interview_session.session_id] = questions_result['questions']
        _current_question_index[interview_session.session_id] = 0
        
        logger.info(f"Stored {len(questions_result['questions'])} questions for session {interview_session.session_id}")
        
        return questions_result['questions']
        
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise e
