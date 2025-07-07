"""
Description:
Extract feedback from content using regex patterns
This module provides a function to extract structured feedback from interview analysis content using predefined regex patterns.

Arguments:
- content: The text content from which to extract feedback.
- request: An instance of InterviewAnalysisRequest containing additional context or parameters.

Returns:
- An instance of InterviewFeedbackResponse containing structured feedback data.

Dependencies:
- app.schemas.session_evaluation_schemas.interview_analysis_request: For defining the request schema.
- app.constants.regex_patterns: For accessing precompiled regex patterns.
- app.schemas.session_evaluation_schemas.interview_feedback_response: For defining the response schema.
- re: Python's built-in regular expression module for pattern matching.

Author: @kcaparas1630

"""
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.constants.regex_patterns import REGEX_PATTERNS
from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse, FollowUpQuestionDetails, NextAction
import json
from loguru import logger

# Extract feedback from the content using regex patterns
def extract_regex_feedback(content: str, request: InterviewAnalysisRequest):
    try:
        # Parse the entire content as a JSON object
        json_data = json.loads(content)

        # Handle the nested next_action and its details
        next_action_data = json_data.get("next_action", {})
        follow_up_details_data = next_action_data.get("follow_up_question_details")

        follow_up_details = None
        if follow_up_details_data:
            follow_up_details = FollowUpQuestionDetails(**follow_up_details_data)

        next_action = NextAction(
            type=next_action_data.get("type", "continue"), # Default to 'continue' if not present
            message=next_action_data.get("message", "Thank you for your response."),
            follow_up_question_details=follow_up_details
        )

        # Create the InterviewFeedbackResponse object
        feedback_response = InterviewFeedbackResponse(
            score=json_data.get("score", 5), # Default to 5 if score is missing
            feedback=json_data.get("feedback", "No specific feedback provided."),
            strengths=json_data.get("strengths", []),
            improvements=json_data.get("improvements", []),
            tips=json_data.get("tips", []),
            engagement_check=json_data.get("engagement_check", False),
            technical_issue_detected=json_data.get("technical_issue_detected", False),
            needs_retry=json_data.get("needs_retry", False),
            next_action=next_action
        )
        return feedback_response

    except json.JSONDecodeError:
        # Fallback: extract only simple fields using regex, always provide default next_action
        def extract_list(pattern, text):
            match = REGEX_PATTERNS[pattern].search(text)
            if match:
                # Split by comma, strip whitespace and quotes
                return [item.strip().strip('"\'') for item in match.group(1).split(',') if item.strip()]
            return []
        def extract_bool(pattern, text):
            match = REGEX_PATTERNS[pattern].search(text)
            if match:
                return match.group(1).lower() == 'true'
            return False
        def extract_int(pattern, text):
            match = REGEX_PATTERNS[pattern].search(text)
            if match:
                return int(match.group(1))
            return 5
        def extract_str(pattern, text):
            match = REGEX_PATTERNS[pattern].search(text)
            if match:
                return match.group(1)
            return "No specific feedback provided."

        score = extract_int('score', content)
        feedback = extract_str('feedback', content)
        strengths = extract_list('strengths', content)
        improvements = extract_list('improvements', content)
        tips = extract_list('tips', content)
        engagement_check = extract_bool('engagement_check', content)
        technical_issue_detected = extract_bool('technical_issue_detected', content)
        needs_retry = extract_bool('needs_retry', content)

        return InterviewFeedbackResponse(
            score=score,
            feedback=feedback,
            strengths=strengths,
            improvements=improvements,
            tips=tips,
            engagement_check=engagement_check,
            technical_issue_detected=technical_issue_detected,
            needs_retry=needs_retry,
            next_action=NextAction(
                type="continue",
                message="There was an issue processing your last response. Let's try again or move on.",
                follow_up_question_details=None
            )
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return InterviewFeedbackResponse(
            score=5,
            feedback="An unexpected error occurred.",
            strengths=[],
            improvements=[],
            tips=[],
            engagement_check=False,
            technical_issue_detected=False,
            needs_retry=False,
            next_action=NextAction(type="continue", message="There was an issue processing your last response. Let's try again or move on.")
        )
    
    