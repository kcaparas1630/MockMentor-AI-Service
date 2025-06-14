from app.schemas.text_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.constants.regex_patterns import REGEX_PATTERNS
from app.schemas.text_schemas.interview_feedback_response import InterviewFeedbackResponse
import re

# Extract feedback from the content using regex patterns
def extract_regex_feedback(content: str, request: InterviewAnalysisRequest):
    # Fallback to more robust regex-based parsing
    feedback_match = REGEX_PATTERNS['feedback'].search(content)
    strengths_match = REGEX_PATTERNS['strengths'].search(content)
    score_match = REGEX_PATTERNS['score'].search(content)
    improvements_match = REGEX_PATTERNS['improvements'].search(content)
    tips_match = REGEX_PATTERNS['tips'].search(content)

    # Parse list items
    def parse_list(match_result):
        if not match_result:
            return []
        items = re.findall(r"[\"'](.*?)[\"']", match_result.group(1))
        return items if items else []
    
    # Create the response object with fallback parsing
    feedback_response = InterviewFeedbackResponse(
        score=int(score_match.group(1)) if score_match else 5,
        feedback=feedback_match.group(1) if feedback_match else "The response shows some understanding of the situation.",
        strengths=parse_list(strengths_match) if strengths_match else ["Clear communication", "Problem-solving approach"],
        improvements=parse_list(improvements_match) if improvements_match else ["Could provide more specific details", "Consider using the STAR method"],
        tips=parse_list(tips_match) if tips_match else ["Practice structuring responses with the STAR method", "Include more quantifiable results"]
    )
                
    return feedback_response
    
    