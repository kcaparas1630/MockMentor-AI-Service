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
from ...schemas.main.user_message import UserMessage
from typing import Dict, List
from starlette.websockets import WebSocket, WebSocketDisconnect
from ...schemas.websocket.websocket_message import WebSocketMessage, WebSocketUserMessage
from .tools.get_questions import get_questions
from ..text_answers_service import analyze_interview_response
from ...schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from .tools.get_conversation_context import get_conversation_context
from .tools.add_to_context import _add_to_context
from .tools.fetch_and_store_questions import _fetch_and_store_questions

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

    
    def _get_current_question(self, session_id: str) -> str:
        """
        Get the current question for the session.
        
        Args:
            session_id (str): The session identifier.
            
        Returns:
            str: The current question or a completion message if all questions are done.
            
        Raises:
            Exception: If no questions are found for the session.
        """
        if session_id not in self._session_questions:
            raise Exception("No questions found for session")
        
        questions = self._session_questions[session_id]
        current_index = self._current_question_index.get(session_id, 0)
        
        if current_index >= len(questions):
            return "We've completed all the questions for this interview session."
        
        return questions[current_index]

    def _advance_to_next_question(self, session_id: str):
        """
        Move to the next question in the sequence.
        
        Args:
            session_id (str): The session identifier.
        """
        if session_id in self._current_question_index:
            self._current_question_index[session_id] += 1

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
            context = get_conversation_context(session_id, self._conversation_contexts)

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
                await _fetch_and_store_questions(interview_session, self._session_questions, self._current_question_index)
                
                # System message with interview guidelines
                system_message = {
                    "role": "system",
                    "content": f"""You are an **expert HR professional and interview coach with 15+ years of experience**. You are inherently **cheerful, encouraging, and provide actionable insights** that help candidates improve their interview performance. Your responses are always **conversational, complete sentences, and avoid jargon or incomplete phrases**.

**Your primary goal is to simulate a realistic, supportive interview environment.**

---

**CRITICAL RULES FOR QUESTIONS:**
1. You MUST NEVER create your own interview questions
2. When the user is ready to start, you will be provided with the EXACT question to ask
3. You MUST use questions EXACTLY as provided - word for word, character for character
4. You MUST NOT modify, rephrase, paraphrase, or change any question in any way

---

**CONVERSATION FLOW:**

1. **Initial Greeting & Setup (Only once, at the very beginning of the session):**
   * Greet the user warmly by their name: "Hi {interview_session.user_name}, thanks for being here today!"
   * Explain the process clearly: "We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach."
   * Initiate the first general readiness check: "Are you ready for your interview?"

2. **When User Confirms Ready:**
   * Acknowledge their readiness enthusiastically
   * Present the exact question provided to you
   * Add encouraging words after the question

3.  **Presenting Interview Questions:**
    * Once the `get_questions` tool provides a question, present it clearly to the user.
    * Reinforce expectations for a good answer (e.g., STAR method if applicable for behavioral questions) and offer encouragement.
    * After the user has answered the question, provide feedback on their response.
    * Move to the next question.

---

**CONTEXT FOR AI'S INTERNAL USE:**

* **sessionId**: {interview_session.session_id}
* **jobRole**: {interview_session.jobRole}
* **jobLevel**: {interview_session.jobLevel}
* **questionType**: {interview_session.questionType}

---

**AVOID:**
* Incomplete sentences or phrases
* Repetitive explanations about the process after the initial greeting
* Providing feedback before the user has given an answer to a specific interview question
* Any response that is not a complete, natural-sounding sentence
* Creating or modifying questions - ALWAYS use the questions provided to you exactly

---

**IMPORTANT NOTE FOR TOOL USAGE:**

* Always preface the actual question with a statement indicating that the `get_questions` tool was called (e.g., "Calling the `get_questions` tool now to retrieve the next question in the sequence. Here it comes:").
"""
                }
                _add_to_context(interview_session.session_id, "system", system_message["content"], self._conversation_contexts)

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
                    current_question = self._get_current_question(session_id)
                    response = f"Great! I'm excited to see how you do. Here's your first question:\n\n{current_question}\n\nTake your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                    _add_to_context(session_id, "assistant", response, self._conversation_contexts)
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
                current_question = self._get_current_question(session_id)
                analysis_request = InterviewAnalysisRequest(
                    jobRole=interview_session.jobRole,
                    jobLevel=interview_session.jobLevel,
                    interviewType=interview_session.questionType,
                    questionType=interview_session.questionType,
                    question=current_question,
                    answer=last_user_message
                )
                analysis_response = await analyze_interview_response(self.client, analysis_request)

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
                
                _add_to_context(session_id, "assistant", feedback_text, self._conversation_contexts)
                self._advance_to_next_question(session_id)

                # Check if more questions remain
                if self._current_question_index[session_id] < len(self._session_questions[session_id]):
                    next_question = self._get_current_question(session_id)
                    response = f"Here's your next question:\n\n{next_question}\n\nTake your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                    _add_to_context(session_id, "assistant", response, self._conversation_contexts)
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

    async def handle_user_message(self, user_message: UserMessage):
        """
        Handle a user's message in an ongoing interview session.
        
        Args:
            user_message (UserMessage): The user's message object.
            
        Returns:
            str: The AI's response to the user's message.
            
        Raises:
            Exception: If there's an error processing the message.
        """
        try:
            _add_to_context(user_message.session_id, "user", user_message.message, self._conversation_contexts)
            
            session = InterviewSession(
                session_id=user_message.session_id,
                user_name="",  # Not needed for ongoing conversation
                jobRole="",   # Not needed for ongoing conversation
                jobLevel="",  # Not needed for ongoing conversation
                questionType=""  # Not needed for ongoing conversation
            )
            return await self.conversation_with_user_response(session)
            
        except Exception as e:
            logger.error(f"Error in handle_user_message: {e}")
            raise e

    async def handle_websocket_connection(self, websocket: WebSocket):
        """
        Handle the entire WebSocket conversation lifecycle.
        
        This method manages the WebSocket connection, including:
        - Initial connection setup
        - Message reception and processing
        - Response sending
        - Error handling
        - Connection cleanup
        
        Args:
            websocket (WebSocket): The WebSocket connection object.
        """
        try:
            # Wait for initial connection message with session details
            initial_message: dict = await websocket.receive_json()
            session = InterviewSession(**initial_message['content'])
            
            # Send initial greeting
            response: str = await self.conversation_with_user_response(session)
            await websocket.send_json(WebSocketMessage(
                type="message",
                content=response
            ).model_dump())

            # Handle ongoing conversation
            while True:
                try:
                    # Process incoming messages
                    raw_message: dict = await websocket.receive_json()
                    user_ws_message: WebSocketUserMessage = WebSocketUserMessage.model_validate(raw_message)
                    
                    user_message: UserMessage = UserMessage(
                        session_id=session.session_id,
                        message=user_ws_message.content
                    )
                    response: str = await self.handle_user_message(user_message)
                    
                    # Send response back to client
                    await websocket.send_json(WebSocketMessage(
                        type="message",
                        content=response
                    ).model_dump())
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed by client")
                    break
                except Exception as e:
                    logger.error(f"Error in websocket message handling: {e}")
                    try:
                        await websocket.send_json(WebSocketMessage(
                            type="error",
                            content=str(e)
                        ).model_dump())
                    except WebSocketDisconnect:
                        logger.info("WebSocket connection closed while sending error")
                        break
        except WebSocketDisconnect:
            logger.info("WebSocket connection closed during initial setup")
        except Exception as e:
            logger.error(f"Error in websocket connection: {e}")
            try:
                await websocket.send_json(WebSocketMessage(
                    type="error",
                    content=str(e)
                ).model_dump())
            except WebSocketDisconnect:
                logger.info("WebSocket connection closed while sending error")
