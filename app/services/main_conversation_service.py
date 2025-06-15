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
"""

import os
from openai import AsyncOpenAI
from loguru import logger
from app.schemas.main.interview_session import InterviewSession
from app.schemas.main.user_message import UserMessage
from typing import Dict, List
from starlette.websockets import WebSocket, WebSocketDisconnect
from app.schemas.websocket.websocket_message import WebSocketMessage, WebSocketUserMessage
from app.services.tools.get_questions import get_questions
import json

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

    def _get_conversation_context(self, session_id: str) -> List[Dict]:
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

    def _add_to_context(self, session_id: str, role: str, content: str):
        """
        Add a message to the conversation context.
        
        Args:
            session_id (str): The session identifier.
            role (str): The role of the message sender (e.g., 'user', 'assistant', 'system').
            content (str): The message content.
        """
        context = self._get_conversation_context(session_id)
        context.append({"role": role, "content": content})

    async def _fetch_and_store_questions(self, interview_session: InterviewSession):
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
            self._session_questions[interview_session.session_id] = questions_result['questions']
            self._current_question_index[interview_session.session_id] = 0
            
            logger.info(f"Stored {len(questions_result['questions'])} questions for session {interview_session.session_id}")
            logger.info(f"First question: {questions_result['questions'][0]}")
            
            return questions_result['questions']
            
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            raise e

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
            context = self._get_conversation_context(interview_session.session_id)
            
            # Handle first message (empty context)
            if not context:
                await self._fetch_and_store_questions(interview_session)
                
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
"""
                }
                self._add_to_context(interview_session.session_id, "system", system_message["content"])

                # Return initial greeting
                return f"Hi {interview_session.user_name}, thanks for being here today! We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach. Are you ready for your interview?"

            # Check if user is expressing readiness to start
            last_user_message = None
            for msg in reversed(context):
                if msg["role"] == "user":
                    last_user_message = msg["content"].lower()
                    break
            
            # Handle user's readiness to start
            if (last_user_message and 
                any(ready_phrase in last_user_message for ready_phrase in ["yes", "ready", "i'm ready", "let's start", "let's go"]) and
                self._current_question_index.get(interview_session.session_id, 0) == 0):
                
                current_question = self._get_current_question(interview_session.session_id)
                self._add_to_context(interview_session.session_id, "user", last_user_message)
                
                response = f"Great! I'm excited to see how you do. Here's your first question:\n\n{current_question}\n\nTake your time, and remember to be specific about your role and the impact you made. I'm looking forward to hearing your response!"
                
                self._add_to_context(interview_session.session_id, "assistant", response)
                self._advance_to_next_question(interview_session.session_id)
                
                return response

            # Generate AI response for ongoing conversation
            response = await self.client.chat.completions.create(
                model="nvidia/Llama-3_1-Nemotron-Ultra-253B-v1",
                max_tokens=1000,
                temperature=0.1,  # Use consistent low temperature for stable responses
                top_p=0.9,
                extra_body={
                    "top_k": 50
                },
                messages=context
            )
            
            message = response.choices[0].message
            content = message.content
            
            if not content:
                content = "I apologize, but I didn't receive a proper response. Let me try again."
            
            # Clean up response content
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            self._add_to_context(interview_session.session_id, "assistant", content)
            
            return content
        
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
            self._add_to_context(user_message.session_id, "user", user_message.message)
            
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
            session = InterviewSession(**initial_message)
            
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
