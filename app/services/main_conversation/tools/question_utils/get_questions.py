"""
Description:
This module provides a function to fetch interview questions from a MongoDB database based on job role, job level, and question type.

Arguments:
- jobRole: The job role for which questions are being fetched (e.g., "Software Engineer").
- jobLevel: The experience level for the job (e.g., "Entry", "Mid", "Senior").
- questionType: The type of questions to fetch (e.g., "Behavioral", "Technical", etc..).

Returns:
- A dictionary containing:
    - success: Boolean indicating if the operation was successful.
    - questions: A list of interview questions matching the criteria.
    - count: The number of questions found.
    - criteria: A dictionary containing the job role, job level, and question type used for the query.

Dependencies:
- pymongo: For MongoDB interactions.
- os: For environment variable access.
- dotenv: For loading environment variables from a .env file.
- loguru: For logging.

author: @kcaparas1630
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client.MockMentor
questions_collection = db.Question

async def get_questions(jobRole: str, jobLevel: str, questionType: str):
    """
        Fetch interview questions from database based on job criteria.
    
    Args:
        jobRole: The job role (e.g., "Software Engineer")
        jobLevel: The experience level (e.g., "Entry", "Mid", "Senior") 
        interviewType: Type of interview (e.g., "Behavioral", "Technical")
    
    Returns:
        Dictionary with questions list and metadata
    """

    try: 
        # Convert interviewType to questionType for database query
        questionType = questionType.lower()
        
        # Log the exact query we're making
        query = {
            "jobRole": jobRole,
            "jobLevel": jobLevel,
            "questionType": questionType
        }
        logger.info(f"Querying MongoDB with: {query}")
        
        # Find questions based on criteria and return both question text and ID
        questions = list(questions_collection.find(
            query,
            {"question": 1, "_id": 1}  # Return both question text and ID
        ))
        
        # Log the raw results for debugging
        logger.info(f"Raw MongoDB results: {questions}")
        
        # Extract question data with both text and ID
        question_data = [
            {
                "id": str(doc["_id"]),
                "text": doc["question"]
            } for doc in questions
        ]
        
        # Also extract just the question texts for backward compatibility
        question_texts = [q["text"] for q in question_data]
        
        logger.info(f"Found {len(question_texts)} questions for {jobRole} {jobLevel} {questionType}")
        
        return {
            "success": True,
            "questions": question_texts,  # Keep for backward compatibility
            "question_data": question_data,  # New field with IDs and texts
            "count": len(question_texts),
            "criteria": {
                "jobRole": jobRole,
                "jobLevel": jobLevel,
                "questionType": questionType
            }
        }
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        return {
            "success": False,
            "error": str(e)
        }
