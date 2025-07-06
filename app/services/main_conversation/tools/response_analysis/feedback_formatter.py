"""
Feedback Formatter Utility Module

This module provides functionality to format analysis responses from the AI service
into readable feedback text for users. It converts structured analysis data into
natural language feedback.

Dependencies:
- app.services.main_conversation.tools.context_utils.get_feedback_opening_line: For feedback opening lines.

Author: @kcaparas1630
"""

from app.services.main_conversation.tools.context_utils.get_feedback_opening_line import get_feedback_opening_line


def format_feedback_response(analysis_response) -> str:
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
    strengths_text = "Here's what you did well: " + ", ".join(analysis_response.strengths) if analysis_response.strengths else ""
    improvements_text = "To make your answer even stronger, consider: " + ", ".join(analysis_response.improvements) if analysis_response.improvements else ""
    tips_text = "Tips for next time: " + ", ".join(analysis_response.tips) if analysis_response.tips else ""

    return (
        f"{get_feedback_opening_line(analysis_response.score)}"
        f"{analysis_response.feedback} "
        f"{strengths_text}. " if strengths_text else ""
        f"{improvements_text}. " if improvements_text else ""
        f"{tips_text}." if tips_text else ""
    )
