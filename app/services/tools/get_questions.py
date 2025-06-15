import json
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
        
        # Find questions based on criteria and only return the question field
        questions = list(questions_collection.find(
            query,
            {"question": 1, "_id": 0}  # Only return the question field
        ))
        
        # Log the raw results for debugging
        logger.info(f"Raw MongoDB results: {questions}")
        
        # Extract just the question text from each document
        question_texts = [doc["question"] for doc in questions]
        
        logger.info(f"Found {len(question_texts)} questions for {jobRole} {jobLevel} {questionType}")
        
        return {
            "success": True,
            "questions": question_texts,  # Return just the list of questions
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
