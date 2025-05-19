from app.schemas.interview_analysis_request import InterviewAnalysisRequest
from app.constants.regex_patterns import REGEX_PATTERNS
from app.schemas.interview_feedback_response import InterviewFeedbackResponse
import re

# Extract feedback from the content using regex patterns
def extract_regex_feedback(content: str, request: InterviewAnalysisRequest):
    # Fallback to more robust regex-based parsing
    overall = REGEX_PATTERNS['overall'].search(content)
    strengths_match = REGEX_PATTERNS['strengths'].search(content)
    areas_match = REGEX_PATTERNS['areas'].search(content)
    score_match = REGEX_PATTERNS['score'].search(content)
    actions_match = REGEX_PATTERNS['actions'].search(content)

    # Parse list items
    def parse_list(match_result):
        if not match_result:
            return []
        items = re.findall(r"[\"'](.*?)[\"']", match_result.group(1))
        return items if items else []        
        # Create the response object with fallback parsing
    feedback_response = InterviewFeedbackResponse(
        question=request.question,
        answer=request.answer,
        overall_assessment=overall.group(1) if overall else "The response shows some understanding of the situation.",
        strengths=parse_list(strengths_match) if strengths_match else ["Clear communication", "Problem-solving approach"],
        areas_for_improvement=parse_list(areas_match) if areas_match else ["Could provide more specific details", "Consider using the STAR method"],
        confidence_score=int(score_match.group(1)) if score_match else 5,
        recommended_actions=parse_list(actions_match) if actions_match else ["Practice structuring responses with the STAR method", "Include more quantifiable results"]
    )
                
    return feedback_response
    
    