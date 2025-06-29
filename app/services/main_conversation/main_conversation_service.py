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

Author: @kcaparas1630
"""

import os
from openai import AsyncOpenAI
from loguru import logger
from ...schemas.main.interview_session import InterviewSession
from typing import Dict, List
from ..speech_to_text.text_answers_service import TextAnswersService
from ...schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from .tools.question_utils.fetch_and_store_questions import fetch_and_store_questions
from .tools.question_utils.get_current_question import get_current_question
from .tools.question_utils.advance_to_next_question import advance_to_next_question
from .tools.context_utils.get_system_prompt import get_system_prompt

class MainConversationService:
    """
    A singleton service class that manages interview conversations.
    
    This class implements the Singleton pattern to ensure only one instance exists
    throughout the application lifecycle. It maintains conversation contexts and
    question sequences for multiple interview sessions.
    
    Attributes:
        _instance: Class variable storing the singleton instance
        _conversation_contexts: Dictionary mapping session IDs to conversation histories
        _session_questions: Dictionary storing questions for each session
        _current_question_index: Dictionary tracking the current question index for each session
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

            # Initialize session state if needed
            if session_id not in self._session_state:
                self._session_state[session_id] = {
                    "ready": False,
                    "current_question_index": 0,
                    "waiting_for_answer": False,
                }
            session_state = self._session_state[session_id]
            
            # Handle first message (empty context)
            if not context:
                await fetch_and_store_questions(interview_session, self._session_questions, self._current_question_index)
                
                # System message with interview guidelines
                system_message = {
                    "role": "system",
                    "content": get_system_prompt(interview_session)
                }
                self.add_to_context(interview_session.session_id, "system", system_message["content"])

                # Return initial greeting
                return f"Hi {interview_session.user_name}, thanks for being here today! We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach. Are you ready for your interview?"

            # Check if user is expressing readiness to start
            last_user_message = None
            for msg in reversed(context):
                if msg["role"] == "user":
                    last_user_message = msg["content"].strip() # remove whitespace
                    break
            
            # Handle readiness
            if not session_state["ready"]:
                ##############################################################################
                #   1. Check if user is ready to start                                       #
                #   2. If user is ready, set session state to ready and waiting for answer.  #
                #   3. Get the current question.                                             #
                #   4. Add the response to the context.                                      #
                #   5. Return the response.                                                  #
                ##############################################################################
                if last_user_message and any(ready in last_user_message.lower() for ready in ["yes", "ready", "i'm ready", "let's start", "let's go"]):
                    session_state["ready"] = True
                    session_state["waiting_for_answer"] = True
                    current_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                    response = f"Great! I'm excited to see how you do. Here's your first question:\n\n{current_question}\n\nTake your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                    self.add_to_context(session_id, "assistant", response)
                    return response
                else:
                    return "Let me know when you're ready to begin!"

            # Handle answer to current question
            if session_state["waiting_for_answer"]:
                ##################################################################################
                #   1. Get the current question.                                                 #
                #   2. Analyze the user's response.                                              #
                #   3. Format the analysis response as a string.                                 #
                #   4. Add the analysis response to the context.                                 #
                #   5. Advance to the next question.                                             #
                #   6. Check if more questions remain.                                           #
                #   7. If more questions remain, set session state to waiting for answer.        #
                #   8. If no more questions remain, set session state to not waiting for answer. #
                #   9. Return the feedback text.                                                 #
                ##################################################################################
                current_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                analysis_request = InterviewAnalysisRequest(
                    jobRole=interview_session.jobRole,
                    jobLevel=interview_session.jobLevel,
                    interviewType=interview_session.questionType,
                    questionType=interview_session.questionType,
                    question=current_question,
                    answer=last_user_message
                )
                text_answers_service = TextAnswersService()
                analysis_response = await text_answers_service.analyze_response(analysis_request)

                # Format the analysis response as a string
                feedback_text = f"""Feedback on your response:
Score: {analysis_response.score}/10
{analysis_response.feedback}

Strengths:
{chr(10).join(f"- {strength}" for strength in analysis_response.strengths)}

Areas for Improvement:
{chr(10).join(f"- {improvement}" for improvement in analysis_response.improvements)}

Tips:
{chr(10).join(f"- {tip}" for tip in analysis_response.tips)}"""
                
                self.add_to_context(session_id, "assistant", feedback_text)
                advance_to_next_question(session_id, self._current_question_index)

                # Check if more questions remain
                if self._current_question_index[session_id] < len(self._session_questions[session_id]):
                    next_question = get_current_question(session_id, self._session_questions, self._current_question_index)
                    response = f"Here's your next question:\n\n{next_question}\n\nTake your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                    self.add_to_context(session_id, "assistant", response)
                    session_state["waiting_for_answer"] = True
                    return feedback_text + "\n\n" + response
                else:
                    session_state["waiting_for_answer"] = False
                    return feedback_text + "\n\nThat's the end of the interview. Great job!"
            
            # Defensive: If not waiting for answer, prompt user
            if not session_state["waiting_for_answer"]:
                return "No rush, take your time to answer the question."
            
        except Exception as e:
            logger.error(f"Error in conversation_with_user_response: {e}")
            raise e

    
