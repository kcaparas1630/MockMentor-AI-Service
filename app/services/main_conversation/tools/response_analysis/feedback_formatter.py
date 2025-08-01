"""
Feedback Formatter Utility Module

This module provides functionality to format analysis responses from the AI service
into readable feedback text for users. It converts structured analysis data into
natural language feedback.

Dependencies:

Author: @kcaparas1630
"""

from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackFormatterResponse
from app.services.main_conversation.tools.context_utils.get_feedback_opening_line import get_feedback_opening_line


def format_feedback_response(analysis_response: InterviewFeedbackFormatterResponse) -> str:
    """
    Format the analysis response into a readable feedback text.
    
    Args:
        analysis_response: The response from TextAnswersService containing
            score, feedback, strengths, improvements, and tips.
            
    Returns:
        str: Formatted feedback text combining all analysis components.
        
    Example:
        >>> response = format_feedback_response(analysis_response)
        >>> print(response)  # "Great job! Your answer was comprehensive..."
    """
    # Generate opening line based on score
    opening_line = get_feedback_opening_line(analysis_response.score)
    
    # Format strengths 
    strengths_text = "Here's what you did well: " + ", ".join(analysis_response.strengths) if analysis_response.strengths else ""
    
    # Format tips 
    tips_text = "Tips for next time: " + ", ".join(analysis_response.tips) if analysis_response.tips else ""

    # Combine all parts with natural flow
    parts = [opening_line, analysis_response.feedback, strengths_text, tips_text]
    formatted_result = " ".join(part.strip() for part in parts if part.strip())
    
    return formatted_result
