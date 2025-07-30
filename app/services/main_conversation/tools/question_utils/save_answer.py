"""
Answer Storage Utility Module

This module provides functionality to save user answers to the MongoDB database.
It handles storing interview responses with session context and metadata.

Dependencies:
- motor: For async MongoDB interactions.
- os: For environment variable access.
- dotenv: For loading environment variables from a .env file.
- loguru: For logging.
- datetime: For timestamping answers.

Author: @kcaparas1630
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from loguru import logger
from datetime import datetime, timezone
from typing import Dict, Any

load_dotenv()

# Initialize async MongoDB client (similar to your working sync version)
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client.MockMentor
answers_collection = db.Answer

async def save_answer(session_id: str, question: str, answer: str, question_index: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Save user answer to MongoDB database.
    
    Args:
        session_id: The interview session identifier
        question: The question that was answered
        answer: The user's response
        question_index: The index of the question in the session
        metadata: Additional session metadata (jobRole, jobLevel, etc.)
    
    Returns:
        Dictionary with success status and saved answer data
    """
    
    try:
        answer_document = {
            "sessionId": session_id,
            "question": question,
            "answer": answer,
            "questionIndex": question_index,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }
        
        # Insert the answer document (direct access like your working version)
        result = await answers_collection.insert_one(answer_document)
        
        logger.info(f"Saved answer for session {session_id}, question {question_index}")
        
        return {
            "success": True,
            "answer_id": str(result.inserted_id),
            "session_id": session_id,
            "question_index": question_index
        }
        
    except Exception as e:
        logger.error(f"Error saving answer: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_session_answers(session_id: str) -> Dict[str, Any]:
    """
    Retrieve all answers for a given session.
    
    Args:
        session_id: The interview session identifier
    
    Returns:
        Dictionary with success status and list of answers
    """
    
    try:
        # Use direct collection access like your working version
        cursor = answers_collection.find(
            {"sessionId": session_id},
            {"_id": 0}  # Exclude MongoDB _id field
        ).sort("questionIndex", 1)  # Sort by question index
        
        answers = await cursor.to_list(length=None)
        
        logger.info(f"Retrieved {len(answers)} answers for session {session_id}")
        
        return {
            "success": True,
            "answers": answers,
            "count": len(answers)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session answers: {e}")
        return {
            "success": False,
            "error": str(e)
        }
