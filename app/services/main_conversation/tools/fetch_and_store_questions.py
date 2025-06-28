from ....schemas.main.interview_session import InterviewSession
from .get_questions import get_questions
from loguru import logger

async def _fetch_and_store_questions(interview_session: InterviewSession, _session_questions: dict, _current_question_index: dict) -> list:
        """
        Fetch questions from database and store them for the session.
        
        Args:
            interview_session (InterviewSession): The interview session object containing job details.
            
        Returns:
            List[str]: The list of questions fetched for the session.
            
        Raises:
            Exception: If questions cannot be fetched or if no questions are found.
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
