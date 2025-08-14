"""
Evaluation Summary Service

This service combines feedback from text analysis and facial landmarks analysis
to create a unified, encouraging summary for interview candidates. It uses the
Nebius API to generate warm, personalized feedback that highlights strengths
and provides actionable improvement tips.

The service integrates with the secure prompt manager to ensure all inputs
are properly sanitized and follows the established feedback format.

Dependencies:
- openai: For Nebius API communication
- loguru: For logging operations
- app.core.ai_client_manager: For dedicated evaluation summary client
- app.core.secure_prompt_manager: For secure prompt handling
"""

import logging
from typing import Optional
from openai import AsyncOpenAI
from app.core.ai_client_manager import get_evaluation_summary_client
from app.core.secure_prompt_manager import secure_prompt_manager
from app.schemas.session_evaluation_schemas import InterviewFeedbackResponse, FacialAnalysisResult

logger = logging.getLogger(__name__)

class EvaluationSummaryService:
    """
    Service for combining text and facial analysis into unified feedback.
    
    This service takes the results from text analysis (score, feedback, strengths, tips)
    and facial landmarks analysis (emotional/behavioral insights) to create a cohesive,
    encouraging summary using the Nebius Llama model.
    """
    
    def __init__(self, client: Optional[AsyncOpenAI] = None):
        """
        Initialize the evaluation summary service.
        
        Args:
            client: Optional AsyncOpenAI client. If not provided, uses dedicated client.
        """
        self.client = client or get_evaluation_summary_client()
        self.model = "meta-llama/Meta-Llama-3.1-8B-Instruct-fast"
    
    async def create_summary(
        self, 
        text_analysis: InterviewFeedbackResponse, 
        facial_analysis: FacialAnalysisResult
    ) -> str:
        """
        Create a unified summary from text and facial analysis results.
        
        Args:
            text_analysis: Results from text analysis containing score, feedback, 
                          strengths, tips, and next_action
            facial_analysis: Results from facial analysis containing feedback
            
        Returns:
            str: Unified encouraging feedback response
            
        Raises:
            ValueError: If required data is missing or invalid
            Exception: If API call fails
        """
        try:
            # Convert results to dicts for the prompt manager
            text_analysis_dict = text_analysis.model_dump()
            facial_analysis_dict = facial_analysis.model_dump()
            
            # Generate secure prompt using the prompt manager
            prompt = secure_prompt_manager.get_summarization_prompt(
                text_analysis=text_analysis_dict,
                facial_analysis=facial_analysis_dict
            )
            
            logger.debug(f"Generated summarization prompt for score {text_analysis.score}")
            
            # Call Nebius API for summary generation
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=512,
                temperature=0.6,
                top_p=0.9,
                presence_penalty=0,
                extra_body={
                    "top_k": 50
                },
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract the summary content
            summary = response.choices[0].message.content.strip()
            
            if not summary:
                raise ValueError("Empty summary received from API")
            
            logger.info(f"Successfully generated summary for score {text_analysis.score}")
            logger.debug(f"Summary preview: {summary[:100]}...")
            
            return summary
            
        except ValueError as e:
            logger.error(f"Validation error in summary creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating evaluation summary: {e}")
            # Return fallback summary to prevent service failure
            return f"Great! You scored a {text_analysis.score}! Your response showed good effort. Keep practicing to improve your interview skills. Ready for the next question?"
    
    async def create_summary_with_fallback(
        self,
        text_analysis: InterviewFeedbackResponse,
        facial_analysis: Optional[FacialAnalysisResult] = None
    ) -> str:
        """
        Create summary with graceful fallback for missing facial analysis.
        
        Args:
            text_analysis: Results from text analysis
            facial_analysis: Optional results from facial analysis
            
        Returns:
            str: Unified feedback response, with or without facial insights
        """
        # Use empty facial analysis if not provided
        if facial_analysis is None:
            facial_analysis = FacialAnalysisResult(feedback="")
        
        try:
            return await self.create_summary(text_analysis, facial_analysis)
        except Exception as e:
            logger.warning(f"Summary creation failed, using fallback: {e}")
            
            # Generate simple fallback based on text analysis only
            strength_text = text_analysis.strengths[0] if text_analysis.strengths else "your effort"
            tip_text = text_analysis.tips[0] if text_analysis.tips else "keep practicing"
            
            return f"Great! You scored a {text_analysis.score}! Your {strength_text} really came through. One tip: {tip_text}. Ready for the next question?"


# Global instance for reuse across the application
evaluation_summary_service = EvaluationSummaryService()
