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
from bson import ObjectId

load_dotenv()

# Initialize async MongoDB client (similar to your working sync version)
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client.MockMentor
interview_collection = db.Interview
interview_question_collection = db.InterviewQuestion

async def save_answer(session_id: str, question: str, answer: str, question_index: int, metadata: Dict[str, Any] = None, feedback_data: Dict[str, Any] = None, session_question_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Save user answer with feedback to MongoDB database using transactions for data consistency.
    
    Args:
        session_id: The interview session identifier
        question: The question that was answered
        answer: The user's response
        question_index: The index of the question in the session
        metadata: Additional session metadata (jobRole, jobLevel, etc.)
        feedback_data: Optional feedback data containing score, tips, and feedback
        session_question_data: Session question data for questionId retrieval
    
    Returns:
        Dictionary with success status and saved answer data
    """
    

    # Validate required parameters
    if not session_id or not question or not answer or question_index is None:
        raise ValueError("session_id, question, answer, and question_index are required parameters")
    if feedback_data and not isinstance(feedback_data, dict):
        raise ValueError("feedback_data must be a dictionary.")
    if session_question_data and not isinstance(session_question_data, dict):
        raise ValueError("session_question_data must be a dictionary.")
    
    # Start a MongoDB transaction session
    async with await client.start_session() as session:
        try:
            async with session.start_transaction():
                # Get questionId from session data if available
                question_id = None
                if session_question_data:
                    if session_id in session_question_data:
                        question_data_list = session_question_data[session_id]
                        if 0 <= question_index < len(question_data_list):
                            question_data_item = question_data_list[question_index]
                            if isinstance(question_data_item, dict) and "id" in question_data_item:
                                question_id = question_data_item["id"]
                                logger.debug(f"Retrieved question_id: {question_id} for index {question_index}")
                            else:
                                logger.warning(f"Question data item missing 'id' key at index {question_index}")
                        else: 
                            logger.warning(f"Question index {question_index} out of bounds for session {session_id}")
                    else:
                        logger.warning(f"Session {session_id} not found in session_question_data")
                else:
                    logger.debug(f"No session_question_data provided for session {session_id}")
                
                # Create InterviewQuestion document
                question_entry = {
                    "interviewId": session_id,  # Link to Interview collection
                    "questionId": question_id,  # Link to Question collection
                    "questionText": question,
                    "answer": answer,
                    "score": feedback_data.get("score") if feedback_data else None,
                    "tips": feedback_data.get("tips", []) if feedback_data else [],
                    "feedback": feedback_data.get("feedback") if feedback_data else None,
                    "answeredAt": datetime.now(timezone.utc)
                }
                
                # Insert into InterviewQuestion collection
                question_result = await interview_question_collection.insert_one(question_entry, session=session)
                question_object_id = question_result.inserted_id
                
                # Update Interview collection: add only the InterviewQuestion ID to questions array
                interview_result = await interview_collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {
                        "$push": {"questions": question_object_id},
                        "$set": {"updatedAt": datetime.now(timezone.utc)}
                    },
                    session=session
                )
                
                if interview_result.matched_count == 0:
                    await session.abort_transaction()
                    logger.warning(f"No interview found with session_id: {session_id}")
                    return {
                        "success": False,
                        "error": f"Interview not found for session {session_id}"
                    }
                
                if interview_result.modified_count == 0:
                    await session.abort_transaction()
                    logger.warning(f"Interview document was not modified for session_id: {session_id}")
                    return {
                        "success": False, 
                        "error": f"Failed to update Interview document for session {session_id}"
                    }
                
                # Commit transaction
                await session.commit_transaction()
                
                logger.info(f"Successfully saved answer for session {session_id}, question {question_index} with transaction")
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "question_index": question_index,
                    "question_id": str(question_object_id),
                    "interview_matched_count": interview_result.matched_count,
                    "interview_modified_count": interview_result.modified_count
                }
                
        except Exception as e:
            await session.abort_transaction()
            logger.error(f"Error saving answer (transaction aborted): {e}")
            return {
                "success": False,
                "error": str(e)
            }

async def get_session_answers(session_id: str) -> Dict[str, Any]:
    """
    Retrieve all answers for a given session by joining Interview and InterviewQuestion collections.
    
    Args:
        session_id: The interview session identifier
    
    Returns:
        Dictionary with success status and list of answers
    """
    
    try:
        # Get the interview document and extract question IDs array
        interview = await interview_collection.find_one(
            {"_id": ObjectId(session_id)},
            {"questions": 1, "_id": 0}  # Only get questions array, exclude _id
        )
        
        if not interview:
            logger.warning(f"No interview found with session_id: {session_id}")
            return {
                "success": False,
                "error": f"Interview not found for session {session_id}"
            }
        
        question_ids = interview.get("questions", [])
        
        if not question_ids:
            logger.info(f"No questions found for session {session_id}")
            return {
                "success": True,
                "answers": [],
                "count": 0
            }
        
        # Retrieve InterviewQuestion documents using the IDs
        questions_cursor = interview_question_collection.find(
            {"_id": {"$in": question_ids}},
            {"_id": 1, "questionText": 1, "answer": 1, "score": 1, "tips": 1, "feedback": 1, "answeredAt": 1, "questionId": 1}
        )
        
        questions = await questions_cursor.to_list(length=None)
        
        # Sort by answeredAt timestamp to maintain chronological order
        questions.sort(key=lambda x: x.get("answeredAt", datetime.min.replace(tzinfo=timezone.utc)))
        
        logger.info(f"Retrieved {len(questions)} answers for session {session_id}")
        
        return {
            "success": True,
            "answers": questions,
            "count": len(questions)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session answers: {e}")
        return {
            "success": False,
            "error": str(e)
        }
