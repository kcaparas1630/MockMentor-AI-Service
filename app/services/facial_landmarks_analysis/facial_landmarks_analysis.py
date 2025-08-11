"""
Facial Landmarks Analysis Service Module

This module provides AI-powered analysis of facial landmarks data to generate
real-time feedback on interview behavior. It analyzes facial expressions, eye contact,
engagement levels, and other non-verbal cues to provide constructive feedback
to interview candidates.

The module implements the same model configuration as the response feedback service
for consistency across the application.

Dependencies:
- openai: For AI client interactions and response generation
- app.core.secure_prompt_manager: For secure prompt management
- logging: For error logging and debugging
- json: For response parsing

Author: @kcaparas1630
"""

from openai import AsyncOpenAI
from app.core.secure_prompt_manager import secure_prompt_manager
from app.core.ai_client_manager import get_facial_analysis_client
import logging
import json
import time
import os

logger = logging.getLogger(__name__)

class FacialLandmarksAnalysis:
    """
    Service class for analyzing facial landmarks data and providing
    real-time behavioral feedback during interviews.
    """
    
    def __init__(self):
        """Initialize the facial landmarks analysis service."""
        pass
    
    async def analyze_landmarks(self, client: AsyncOpenAI = None, landmarks_data: str = "") -> dict:
        """
        Analyze facial landmarks data and provide behavioral feedback.
        
        Args:
            client (AsyncOpenAI): The OpenAI client instance
            landmarks_data (str): The facial landmarks data to analyze
            
        Returns:
            dict: Analysis result containing feedback
            
        Raises:
            Exception: If there's a critical error in the analysis process
        """
        try:
            logger.info(f"[ENTRY] analyze_landmarks function called - ENTRY POINT")
            
            total_start_time = time.time()
            
            # Use dedicated client if not provided
            if client is None:
                client = get_facial_analysis_client()
                logger.debug("Using dedicated facial analysis client")
            else:
                logger.debug("Using provided client for facial analysis")
            
            # Use secure prompt manager to generate safe prompt
            system_prompt = secure_prompt_manager.get_facial_landmarks_analysis_prompt(landmarks_data)
            
            llm_start_time = time.time()
            
            response = await client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-8B-Instruct-fast",
                max_tokens=500,
                temperature=0.1,
                top_p=0.9,
                extra_body={
                    "top_k": 50
                },
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Please analyze these facial landmarks: {landmarks_data}"
                            }
                        ]
                    }
                ]
            )
            
            llm_duration = time.time() - llm_start_time
            logger.info(f"LLM call completed in {llm_duration:.3f}s")
            
            content = response.choices[0].message.content
            
            # Log the raw AI response for debugging
            logger.info(f"[FACIAL_ANALYSIS] Raw AI response: {content}")
            print(f"Response content: {content}")
            
            # Parse JSON response
            try:
                feedback_data = json.loads(content.strip())
                logger.info(f"[FACIAL_ANALYSIS] Successfully parsed JSON: {feedback_data}")
                
                total_duration = time.time() - total_start_time
                logger.info(f"[PERF] Total analyze_landmarks completed in {total_duration:.3f}s")
                
                return feedback_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Content that failed to parse: {content}")
                
                # Try to extract JSON from the response if it's mixed with other text
                import re
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    try:
                        fallback_data = json.loads(json_match.group())
                        logger.info(f"Successfully extracted JSON from mixed response: {fallback_data}")
                        return fallback_data
                    except json.JSONDecodeError:
                        pass
                
                # Return structured fallback response
                return {
                    "feedback": "I'm ready to analyze your behavior, but I need clearer facial landmark data. Please ensure good lighting and face the camera directly for the best analysis."
                }
                
        except Exception as e:
            logger.error(f"[ERROR] Exception in analyze_landmarks: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[ERROR] Full traceback: {traceback.format_exc()}")
            
            # Return error response
            return {
                "feedback": "Technical error occurred during facial analysis. Please try again."
            }

# Global instance for reuse across the application
facial_landmarks_analyzer = FacialLandmarksAnalysis()