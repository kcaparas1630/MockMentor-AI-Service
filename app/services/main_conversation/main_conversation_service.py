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
from app.core.ai_client_manager import get_conversation_client, get_text_analysis_client
from loguru import logger
from app.schemas.main.interview_session import InterviewSession
from typing import Dict, List
from app.core.secure_prompt_manager import sanitize_text
from app.schemas.session_evaluation_schemas import SessionMetadata, SessionStateDict
from app.services.main_conversation.tools.question_utils.fetch_and_store_questions import fetch_and_store_questions
from app.services.main_conversation.tools.question_utils.get_current_question import get_current_question
from app.services.main_conversation.tools.question_utils.advance_to_next_question import advance_to_next_question
from app.services.main_conversation.tools.context_utils.get_system_prompt import get_system_prompt
from app.services.main_conversation.tools.conversation_flow import (
    handle_readiness_check,
    process_user_answer
)
from app.services.main_conversation.tools.response_analysis import (
    format_feedback_response,
    handle_next_action
)
from app.services.main_conversation.tools.response_analysis.action_handlers import reset_question_attempts
from app.services.main_conversation.tools.question_utils.advance_to_next_question import advance_to_next_question
from app.services.main_conversation.tools.question_utils.get_current_question import get_current_question
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
    _session_state_dict: SessionStateDict = SessionStateDict() # Track session state with type safety
    _session_question_data: Dict[str, List[Dict]] = {} # Store question data with IDs for each session

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
            # Use dedicated client for conversation services (lazy initialization)
            cls._instance.client = get_conversation_client()
            cls._instance.text_analysis_client = get_text_analysis_client()
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
            if self._session_state_dict.session_exists(session_id):
                raise BadRequest(f"Session {session_id} already exists. Use continue_conversation for ongoing sessions.")
            
            # Create typed session metadata
            session_metadata = SessionMetadata(
                user_name=interview_session.user_name,
                jobRole=interview_session.jobRole,
                jobLevel=interview_session.jobLevel,
                questionType=interview_session.questionType
            )
            
            # Initialize typed session state
            session_state = self._session_state_dict.create_session(session_id, session_metadata)
            
            # Fetch and store questions
            await fetch_and_store_questions(interview_session, self._session_questions, self._current_question_index, self._session_question_data)
            
            # Determine system prompt: custom or default
            try:
                raw_instruction = getattr(interview_session, "custom_instruction", None)
                custom_prompt = sanitize_text(raw_instruction) if raw_instruction else None
            except ValueError as e:
                custom_prompt = None
                logger.warning(f"[Session {session_id}] Invalid custom instruction provided: {e}")

            if custom_prompt:
                logger.info(f"[Session {session_id}] Using custom instruction prompt.")
                system_prompt = custom_prompt
            else:
                logger.info(f"[Session {session_id}] Using default system prompt.")
                system_prompt = get_system_prompt(interview_session)

            # Add system message to context
            self.add_to_context(session_id, "system", system_prompt)

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
        
        This method orchestrates the conversation flow by delegating to specialized
        utility modules for different conversation states and actions.
        
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
            
            # Validate session state
            session_state = self._session_state_dict.get_session(session_id)
            if session_state is None:
                raise NotFound(f"Session {session_id} not found. Initialize session first.")
            last_user_message = user_message.strip()
            
            # Handle readiness check
            if not session_state.ready:
                return handle_readiness_check(
                    session_id, last_user_message, session_state,
                    self._session_questions, self._current_question_index, self.add_to_context
                )
            
            # Handle answer processing
            if session_state.waiting_for_answer:
                return await process_user_answer(
                    session_id, last_user_message, session_state,
                    self._session_questions, self._current_question_index, self.text_analysis_client,
                    self.add_to_context, format_feedback_response,
                    lambda session_id, analysis_response, feedback_text, session_state: handle_next_action(
                        session_id, analysis_response, feedback_text, session_state,
                        self._session_questions, self._current_question_index,
                        self.add_to_context, advance_to_next_question, get_current_question, reset_question_attempts
                    ),
                    self._session_question_data
                )
            
            # Defensive: If not waiting for answer, prompt user
            return "No rush, take your time to answer the question."

        except BadRequest:
            raise
        except NotFound:
            raise
        except Exception as e:
            logger.error(f"Error in continue_conversation: {e}")
            raise InternalServerError("An unexpected error occurred during conversation continuation.")



    
