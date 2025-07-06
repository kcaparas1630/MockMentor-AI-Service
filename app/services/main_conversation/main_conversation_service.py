"""
Main Conversation Service Module

This module implements a singleton service that manages interview conversations between users and an AI interviewer.
It handles the entire lifecycle of an interview session, including:
- Initial session setup
- Question management
- Conversation context maintenance
- WebSocket communication
- AI response generation

The service uses the Nebius API for AI interactions and maintains conversation state for multiple sessions.

Dependencies:
- openai: For AI client interactions.
- loguru: For logging information and errors.
- app.schemas: For defining data models used in the service.
- app.services.main_conversation.tools.get_questions: For fetching interview questions from the database.
- app.services.text_answers_service: For analyzing user responses and generating feedback.
- app.schemas.session_evaluation_schemas.interview_analysis_request: For defining the request schema for interview analysis.
- starlette.websockets: For handling WebSocket connections and messages.
- app.schemas.websocket.websocket_message: For defining WebSocket message structures.
- app.schemas.main.interview_session: For defining the interview session schema.
- app.schemas.main.user_message: For defining user message schema.
- app.schemas.websocket.websocket_user_message: For defining WebSocket user message schema.
- app.schemas.main.interview_session: For defining the interview session schema.
- app.schemas.main.user_message: For defining user message schema.
- app.errors.exceptions: For handling exceptions.

Author: @kcaparas1630
"""

import os
from openai import AsyncOpenAI
from loguru import logger
from app.schemas.main.interview_session import InterviewSession
from typing import Dict, List
from app.services.speech_to_text.text_answers_service import TextAnswersService
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.services.main_conversation.tools.question_utils.fetch_and_store_questions import fetch_and_store_questions
from app.services.main_conversation.tools.question_utils.get_current_question import get_current_question
from app.services.main_conversation.tools.question_utils.advance_to_next_question import advance_to_next_question
from app.services.main_conversation.tools.context_utils.get_system_prompt import get_system_prompt
from app.services.main_conversation.tools.context_utils.get_feedback_opening_line import get_feedback_opening_line
from app.errors.exceptions import BadRequest, NotFound, InternalServerError

class MainConversationService:
    """
    A singleton service class that manages interview conversations.
    
    This class implements the Singleton pattern to ensure only one instance exists
    throughout the application lifecycle. It maintains conversation contexts and
    question sequences for multiple interview sessions.
    
    The service provides three main methods for different use cases:
    
    1. initialize_session(): For setting up a new interview session
    2. continue_conversation(): For ongoing conversations (only needs session_id and message)
    3. conversation_with_user_response(): Legacy method that handles both initialization and continuation
    
    Attributes:
        _instance: Class variable storing the singleton instance
        _conversation_contexts: Dictionary mapping session IDs to conversation histories
        _session_questions: Dictionary storing questions for each session
        _current_question_index: Dictionary tracking the current question index for each session
        _session_state: Dictionary tracking session state for each session
        
    Example Usage:
        # Initialize a new session
        service = MainConversationService()
        session = InterviewSession(
            session_id="123",
            user_name="John Doe",
            jobRole="Software Engineer",
            jobLevel="Mid-level",
            questionType="Behavioral"
        )
        greeting = await service.initialize_session(session)
        
        # Continue conversation (only needs session_id and message)
        response = await service.continue_conversation("123", "I'm ready to start")
        response = await service.continue_conversation("123", "My answer to the question...")
    """
    
    _instance = None  # Class variable to store the singleton instance
    _conversation_contexts: Dict[str, List[Dict]] = {}  # Store conversation history for each session
    _session_questions: Dict[str, List[str]] = {}  # Store questions for each session
    _current_question_index: Dict[str, int] = {}  # Track current question index for each session
    _session_state: Dict[str, Dict] = {} # Track session state for each session

    def __new__(cls):
        """
        Implements the Singleton pattern.
        
        Returns:
            MainConversationService: The singleton instance of the service.
            
        Raises:
            RuntimeError: If the NEBIUS_API_KEY environment variable is not set.
        """
        if cls._instance is None:
            cls._instance = super(MainConversationService, cls).__new__(cls)
            # Initialize the instance with Nebius API client
            api_key = os.getenv("NEBIUS_API_KEY")
            if not api_key:
                raise RuntimeError("NEBIUS_API_KEY environment variable is not set")
            cls._instance.client = AsyncOpenAI(
                base_url="https://api.studio.nebius.com/v1",
                api_key=api_key)
        return cls._instance
    

    def get_conversation_context(self, session_id: str) -> List[Dict]:
        """
        Get or initialize conversation context for a session.
        
        Args:
            session_id (str): The unique identifier for the interview session.
            
        Returns:
            List[Dict]: The conversation context for the specified session.
        """
        if session_id not in self._conversation_contexts:
            self._conversation_contexts[session_id] = []
        return self._conversation_contexts[session_id]

    def add_to_context(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation context.
        
        Args:
            session_id (str): The session identifier.
            role (str): The role of the message sender (e.g., 'user', 'assistant', 'system').
            content (str): The message content.
        """
        context = self.get_conversation_context(session_id)
        context.append({"role": role, "content": content})

    async def conversation_with_user_response(self, interview_session: InterviewSession):
        """
        Main conversation orchestrator that handles both initial setup and ongoing conversation.
        
        This method manages the entire conversation flow, including:
        - Initial session setup with system message
        - Question presentation
        - User response handling
        - AI response generation
        
        Args:
            interview_session (InterviewSession): The interview session object.
            
        Returns:
            str: The response message to be sent to the user.
            
        Raises:
            Exception: If there's an error in conversation processing.
        """
        try:
            # Initialize or get conversation context
            session_id = interview_session.session_id
            context = self.get_conversation_context(session_id)

            # Handle first message (empty context) - initialize session
            if not context:
                return await self.initialize_session(interview_session)
            
            return None
            
        except BadRequest:
            raise
        except NotFound:
            raise
        except Exception as e:
            logger.error(f"Error in conversation_with_user_response: {e}")
            raise InternalServerError("An unexpected error occurred during conversation setup.")

    async def initialize_session(self, interview_session: InterviewSession) -> str:
        """
        Initialize a new interview session.
        
        This method sets up a new interview session with questions, system prompts,
        and initial greeting. It should be called only once per session.
        
        Args:
            interview_session (InterviewSession): The interview session object with all required metadata.
            
        Returns:
            str: The initial greeting message for the user.
            
        Raises:
            Exception: If there's an error in session initialization.
        """
        try:
            session_id = interview_session.session_id
            
            # Check if session already exists
            if session_id in self._session_state:
                raise BadRequest(f"Session {session_id} already exists. Use continue_conversation for ongoing sessions.")
            
            # Initialize session state
            self._session_state[session_id] = {
                "ready": False,
                "current_question_index": 0,
                "waiting_for_answer": False,
                "retry_attempts": 0,  # Track retry attempts for current question
                "follow_up_attempts": 0,  # Track follow-up attempts for current question
                "session_metadata": {
                    "user_name": interview_session.user_name,
                    "jobRole": interview_session.jobRole,
                    "jobLevel": interview_session.jobLevel,
                    "questionType": interview_session.questionType
                }
            }
            
            # Fetch and store questions
            await fetch_and_store_questions(interview_session, self._session_questions, self._current_question_index)
            
            # Add system message
            system_message = {
                "role": "system",
                "content": get_system_prompt(interview_session)
            }
            self.add_to_context(session_id, "system", system_message["content"])

            # Return initial greeting
            return f"Hi {interview_session.user_name}, thanks for being here today! We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach. Are you ready for your interview?"
            
        except BadRequest:
            raise
        except Exception as e:
            logger.error(f"Error in initialize_session: {e}")
            raise InternalServerError("An unexpected error occurred during session initialization.")

    async def continue_conversation(self, session_id: str, user_message: str) -> str:
        """
        Continue an ongoing conversation with just session_id and user message.
        
        This method is designed for ongoing conversations where the session is already
        initialized and we only need to process the user's message.
        
        Args:
            session_id (str): The unique identifier for the interview session.
            user_message (str): The user's message content.
            
        Returns:
            str: The response message to be sent to the user.
            
        Raises:
            Exception: If there's an error in conversation processing.
        """
        try:
            # Add user message to context
            self.add_to_context(session_id, "user", user_message)
            
            # Get conversation context
            context = self.get_conversation_context(session_id)
            
            # Ensure session state exists
            if session_id not in self._session_state:
                raise NotFound(f"Session {session_id} not found. Session must be initialized first.")
            
            session_state = self._session_state[session_id]
            
            # Get the last user message (which we just added)
            last_user_message = user_message.strip()
            
            # Handle readiness
            if not session_state["ready"]:
                if last_user_message and any(ready in last_user_message.lower() for ready in ["yes", "ready", "i'm ready", "let's start", "let's go"]):
                    session_state["ready"] = True
                    session_state["waiting_for_answer"] = True
                    current_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                    response = f"Great! I'm excited to see how you do. Here's your first question {current_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                    self.add_to_context(session_id, "assistant", response)
                    return response
                else:
                    return "Let me know when you're ready to begin!"

            # Handle answer to current question
            if session_state["waiting_for_answer"]:
                if "session_metadata" not in session_state:
                    raise BadRequest(f"Session {session_id} metadata not found. Session must be properly initialized.")
                
                session_metadata = session_state["session_metadata"]
                current_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                analysis_request = InterviewAnalysisRequest(
                    jobRole=session_metadata["jobRole"],
                    jobLevel=session_metadata["jobLevel"],
                    interviewType=session_metadata["questionType"],
                    questionType=session_metadata["questionType"],
                    question=current_question,
                    answer=last_user_message
                )
                text_answers_service = TextAnswersService(self.client)
                analysis_response = await text_answers_service.analyze_response(analysis_request)

                # Format the analysis response as a string
                # Convert lists to readable text format
                strengths_text = ", ".join(analysis_response.strengths) if analysis_response.strengths else "No specific strengths identified"
                improvements_text = ", ".join(analysis_response.improvements) if analysis_response.improvements else "No specific improvements needed"
                tips_text = ", ".join(analysis_response.tips) if analysis_response.tips else "No specific tips provided"
                
                feedback_text = (
                    f"{get_feedback_opening_line(analysis_response.score)}"
                    f"{analysis_response.feedback} "
                    f"Here's what you did well: {strengths_text}. "
                    f"To make your answer even stronger, consider: {improvements_text}. "
                    f"Tips for next time: {tips_text}."
                )

                # Always add feedback to context
                self.add_to_context(session_id, "assistant", feedback_text)

                # Handle technical issues or retry (limit to 1 retry per question)
                if (analysis_response.technical_issue_detected or analysis_response.needs_retry) and session_state["retry_attempts"] < 1:
                    session_state["retry_attempts"] += 1
                    retry_message = analysis_response.next_action.message
                    self.add_to_context(session_id, "assistant", retry_message)
                    return feedback_text + retry_message
                elif (analysis_response.technical_issue_detected or analysis_response.needs_retry) and session_state["retry_attempts"] >= 1:
                    # Max retries reached, move to next question
                    advance_to_next_question(session_id, self._current_question_index)
                    if self._current_question_index[session_id] < len(self._session_questions[session_id]):
                        next_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                        next_message = f"Let's move on to the next question: {next_question} Take your time, and remember to be specific about your role and the impact you made."
                        self.add_to_context(session_id, "assistant", next_message)
                        session_state["waiting_for_answer"] = True
                        session_state["retry_attempts"] = 0  # Reset for new question
                        session_state["follow_up_attempts"] = 0  # Reset for new question
                        return feedback_text + "Due to technical difficulties, let's move on to the next question. " + next_message
                    else:
                        session_state["waiting_for_answer"] = False
                        end_message = "That's the end of the interview. Great job!"
                        self.add_to_context(session_id, "assistant", end_message)
                        return feedback_text + "Due to technical difficulties, let's conclude the interview. " + end_message

                # Handle engagement check and follow-up (limit to 1 follow-up per question)
                if analysis_response.engagement_check and analysis_response.next_action.type == "ask_follow_up" and session_state["follow_up_attempts"] < 1:
                    session_state["follow_up_attempts"] += 1
                    follow_up_message = analysis_response.next_action.message
                    # Optionally include follow-up details if present
                    if analysis_response.next_action.follow_up_question_details:
                        details = analysis_response.next_action.follow_up_question_details
                        follow_up_message += f" Follow-up: {details.original_question} (Gap: {details.specific_gap_identified})"
                    self.add_to_context(session_id, "assistant", follow_up_message)
                    return feedback_text + follow_up_message
                elif analysis_response.engagement_check and analysis_response.next_action.type == "ask_follow_up" and session_state["follow_up_attempts"] >= 1:
                    # Max follow-ups reached, move to next question
                    advance_to_next_question(session_id, self._current_question_index)
                    if self._current_question_index[session_id] < len(self._session_questions[session_id]):
                        next_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                        next_message = f"Let's move on to the next question: {next_question} Take your time, and remember to be specific about your role and the impact you made."
                        self.add_to_context(session_id, "assistant", next_message)
                        session_state["waiting_for_answer"] = True
                        session_state["retry_attempts"] = 0  # Reset for new question
                        session_state["follow_up_attempts"] = 0  # Reset for new question
                        return feedback_text + "Let's move on to the next question. " + next_message
                    else:
                        session_state["waiting_for_answer"] = False
                        end_message = "That's the end of the interview. Great job!"
                        self.add_to_context(session_id, "assistant", end_message)
                        return feedback_text + "Let's conclude the interview. " + end_message

                # Handle suggest_exit
                if analysis_response.next_action.type == "suggest_exit":
                    exit_message = analysis_response.next_action.message
                    self.add_to_context(session_id, "assistant", exit_message)
                    session_state["waiting_for_answer"] = False
                    return feedback_text + exit_message

                # Handle continue (advance to next question)
                if analysis_response.next_action.type == "continue":
                    advance_to_next_question(session_id, self._current_question_index)
                    # Check if more questions remain
                    if self._current_question_index[session_id] < len(self._session_questions[session_id]):
                        next_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                        next_message = f"Here's your next question: {next_question} Take your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                        self.add_to_context(session_id, "assistant", next_message)
                        session_state["waiting_for_answer"] = True
                        session_state["retry_attempts"] = 0  # Reset for new question
                        session_state["follow_up_attempts"] = 0  # Reset for new question
                        return feedback_text + analysis_response.next_action.message + next_message
                    else:
                        session_state["waiting_for_answer"] = False
                        end_message = analysis_response.next_action.message + "That's the end of the interview. Great job!"
                        self.add_to_context(session_id, "assistant", end_message)
                        return feedback_text + end_message

                # Defensive: If not waiting for answer, prompt user
                if not session_state["waiting_for_answer"]:
                    return "No rush, take your time to answer the question."

        except BadRequest:
            raise
        except NotFound:
            raise
        except Exception as e:
            logger.error(f"Error in continue_conversation: {e}")
            raise InternalServerError("An unexpected error occurred during conversation continuation.")

    
