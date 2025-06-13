import os
from openai import AsyncOpenAI
from loguru import logger
from app.schemas.main.interview_session import InterviewSession
from app.schemas.main.user_message import UserMessage
from typing import Dict, List
from starlette.websockets import WebSocketDisconnect
from app.schemas.websocket.websocket_message import WebSocketMessage, WebSocketUserMessage

class MainConversationService:
    _instance = None # CLass variable to store the instance of the class
    _conversation_contexts: Dict[str, List[Dict]] = {} 

    def __new__(cls): #cls means class
        if cls._instance is None: # if no instance then create a new instance
            cls._instance = super(MainConversationService, cls).__new__(cls)
            # Initialize the instance
            api_key = os.getenv("NEBIUS_API_KEY")
            if not api_key:
                raise RuntimeError("NEBIUS_API_KEY environment variable is not set")
            cls._instance.client = AsyncOpenAI(
                base_url="https://api.studio.nebius.com/v1",
                api_key=api_key)
        return cls._instance # return the instance
    # Get the conversation context of a session
    def _get_conversation_context(self, session_id: str) -> List[Dict]:
        """Get or initialize conversation context for a session"""
        if session_id not in self._conversation_contexts:
            self._conversation_contexts[session_id] = []
        return self._conversation_contexts[session_id]
    # Add a message to the conversation context
    def _add_to_context(self, session_id: str, role: str, content: str):
        """Add a message to the conversation context"""
        # Get the conversation context first before appending the new message.
        context = self._get_conversation_context(session_id)
        context.append({"role": role, "content": content})
        # Log the current context for the session for debugging purposes
        logger.info(f"Current context for session {session_id}: {context}")

    # Main conversation orchestrator - handles both initial setup and ongoing conversation
    async def conversation_with_user_response(self, interview_session: InterviewSession): 
        """
        Main conversation orchestrator - handles both initial setup and ongoing conversation
        """
        try:
            # Initialize or get conversation context
            context = self._get_conversation_context(interview_session.session_id)
            logger.info(f"Retrieved context: {context}")
            
            # If this is the first message (empty context), add system message
            if not context:
                system_message = {
                    "role": "system",
                    "content": f"""You are an **expert HR professional and interview coach with 15+ years of experience**. You are inherently **cheerful, encouraging, and provide actionable insights** that help candidates improve their interview performance. Your responses are always **conversational, complete sentences, and avoid jargon or incomplete phrases**.

**Your primary goal is to simulate a realistic, supportive interview environment.**
---

**CONVERSATION FLOW:**

1.  **Initial Greeting & Setup (Only once, at the very beginning of the session):**
    * Greet the user warmly by their name: "Hi {interview_session.user_name}, thanks for being here today!"
    * Explain the process clearly: "We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach."
    * Initiate the first general readiness check: "Are you ready for your interview?"

2.  **Handling "Ready" Confirmation:**
    * If the user confirms readiness (e.g., "Yes", "I'm ready"), respond enthusiastically, acknowledge their readiness.
    ---

**CONTEXT FOR AI'S INTERNAL USE:**

* **sessionId**: {interview_session.session_id} (Unique identifier for the current interview session.)
* **job_role**: {interview_session.job_role} (The specific job role the user is interviewing for, e.g., "Software Engineer", "Project Manager".)
* **job_level**: {interview_session.job_level} (The seniority level of the role, e.g., "entry", "mid", "senior".)
* **interview_type**: {interview_session.interview_type} (The type of interview, e.g., "behavioral", "technical", "case_study".)

*(The above context parameters will be passed by the client to inform tool calls like `get_questions`.)*

---

**AVOID:**

* Incomplete sentences or phrases.
* Repetitive explanations about the process after the initial greeting.
* Providing feedback before the user has given an answer to a specific interview question.
* Any response that is not a complete, natural-sounding sentence.
* Including your internal thinking process or reasoning in the response.
* Using tags like <think> or any other markers in your response.

---
"""
                }
                self._add_to_context(interview_session.session_id, "system", system_message["content"])

            # Get response from AI
            response = await self.client.chat.completions.create(
                model="nvidia/Llama-3_1-Nemotron-Ultra-253B-v1",
                max_tokens=1000,
                temperature=0.5,
                top_p=0.9,
                extra_body={
                    "top_k": 50
                },
                messages=context
            )
            
            content = response.choices[0].message.content
            # Remove the <think> section if it exists
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            # Add AI's response to context
            self._add_to_context(interview_session.session_id, "assistant", content)
            
            logger.info(f"Generated response: {content}")
            return content
        
        except Exception as e:
            logger.error(f"Error in conversation_with_user_response: {e}")
            raise e

    async def handle_user_message(self, user_message: UserMessage):
        """
        Handle a user's message in an ongoing interview session
        """
        try:
            # Add user's message to context
            self._add_to_context(user_message.session_id, "user", user_message.message)
            
            # Get response using the main conversation method
            # Create a InterviewSession object with only the session_id
            session = InterviewSession(
                session_id=user_message.session_id,
                user_name="",  # Not needed for ongoing conversation
                job_role="",   # Not needed for ongoing conversation
                job_level="",  # Not needed for ongoing conversation
                interview_type=""  # Not needed for ongoing conversation
            )
            return await self.conversation_with_user_response(session)
            
        except Exception as e:
            logger.error(f"Error in handle_user_message: {e}")
            raise e

    async def handle_websocket_connection(self, websocket):
        """
        Handle the entire WebSocket conversation lifecycle
        """
        try:
            # Wait for initial connection message with session details
            initial_message = await websocket.receive_json()
            session = InterviewSession(**initial_message)
            
            # Get initial greeting
            response = await self.conversation_with_user_response(session)
            await websocket.send_json({"type": "message", "content": response})

            # Handle ongoing conversation
            while True:
                try:
                    # Wait for user message
                    message = await websocket.receive_json()
                    
                    # Process message and get response
                    user_message = UserMessage(
                        session_id=session.session_id,
                        message=message["content"]
                    )
                    response = await self.handle_user_message(user_message)
                    
                    # Send response back
                    await websocket.send_json({
                        "type": "message",
                        "content": response
                    })
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed by client")
                    break
                except Exception as e:
                    logger.error(f"Error in websocket message handling: {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "content": str(e)
                        })
                    except WebSocketDisconnect:
                        logger.info("WebSocket connection closed while sending error")
                        break
        except WebSocketDisconnect:
            logger.info("WebSocket connection closed during initial setup")
        except Exception as e:
            logger.error(f"Error in websocket connection: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })
            except WebSocketDisconnect:
                logger.info("WebSocket connection closed while sending error")
