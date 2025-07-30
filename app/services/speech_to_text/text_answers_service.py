"""
Text Answers Service Module

This module provides a service class for analyzing interview responses and generating
comprehensive feedback. It acts as a wrapper around the response feedback functionality,
providing a clean interface for interview response analysis.

The module contains a service class that manages the analysis workflow, including
client initialization and response processing. It serves as the primary interface
for interview response analysis in the speech-to-text service layer.

Dependencies:
- openai: For AI client interactions.
- loguru: For logging operations.
- app.schemas.session_evaluation_schemas: For interview analysis and feedback data models.
- app.services.speech_to_text.tools.response_feedback: For the core response analysis functionality.

Author: @kcaparas1630
"""

from openai import AsyncOpenAI
from loguru import logger
from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse
from app.schemas.session_evaluation_schemas.interview_request import InterviewRequest
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.services.speech_to_text.tools.response_feedback import response_feedback

class TextAnswersService:
    """
    Service class for analyzing interview responses and providing feedback.
    
    This class provides a high-level interface for interview response analysis,
    encapsulating the complexity of AI-powered feedback generation. It manages
    the OpenAI client and coordinates the analysis workflow.
    
    The service is designed to be instantiated once and reused for multiple
    interview response analyses, providing consistent feedback quality and
    efficient resource utilization.
    
    Attributes:
        client (AsyncOpenAI): The OpenAI client instance used for AI interactions.
    """
    
    def __init__(self, client: AsyncOpenAI):
        """
        Initialize the service with an OpenAI client.
        
        This constructor sets up the service with the provided OpenAI client,
        which will be used for all subsequent interview response analyses.
        
        Args:
            client (AsyncOpenAI): The OpenAI client instance configured with
                appropriate API credentials and settings.
                
        Example:
            >>> from openai import AsyncOpenAI
            >>> client = AsyncOpenAI(api_key="your-api-key")
            >>> service = TextAnswersService(client)
        """
        self.client = client
    
    async def analyze_response(self, analysis_request: InterviewAnalysisRequest) -> InterviewFeedbackResponse:
        """
        Analyze an interview response and provide feedback.
        
        This method processes an interview response using AI-powered analysis
        to generate comprehensive feedback including scores, strengths, areas
        for improvement, and actionable tips.
        
        The analysis considers the specific job role, level, and question type
        to provide tailored feedback that helps candidates improve their
        interview performance.
        
        Args:
            analysis_request (InterviewAnalysisRequest): The request containing
                the interview details (job role, level, question type) and the
                candidate's response to analyze.
                
        Returns:
            InterviewFeedbackResponse: The analysis results containing:
                - score: Integer score from 1-10
                - feedback: Brief summary of the response
                - strengths: List of positive aspects identified
                - improvements: List of areas for improvement
                - tips: List of actionable advice
                
        Raises:
            Exception: If there's an error during the analysis process or
                if the AI service is unavailable.
                
        Example:
            >>> request = InterviewAnalysisRequest(
            ...     jobRole="Software Engineer",
            ...     jobLevel="Mid",
            ...     interviewType="Behavioral",
            ...     questionType="Behavioral",
            ...     question="Tell me about a challenging project you worked on.",
            ...     answer="I led a team of 5 developers..."
            ... )
            >>> feedback = await service.analyze_response(request)
            >>> print(f"Score: {feedback.score}/10")
            >>> print(f"Feedback: {feedback.feedback}")
        """
        result = await response_feedback(self.client, analysis_request)
        return result
