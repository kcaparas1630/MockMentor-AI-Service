"""
Response Feedback Analysis Tool Module

This module provides the core functionality for analyzing interview responses and
generating comprehensive feedback using AI. It implements the main analysis logic
that evaluates candidate responses based on job criteria and provides structured
feedback including scores, strengths, improvements, and actionable tips.

The module contains a single async function that orchestrates the complete analysis
workflow, including AI prompt generation, response parsing, and fallback error
handling. It serves as the primary analysis engine for interview feedback generation.

Dependencies:
- openai: For AI client interactions and response generation.
- app.schemas.session_evaluation_schemas: For interview analysis and feedback data models.
- app.helper.extract_regex_feedback: For fallback regex-based feedback extraction.
- logging: For error logging and debugging.

Author: @kcaparas1630
"""

from openai import AsyncOpenAI
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse, NextAction
from app.schemas.session_evaluation_schemas.interview_request import InterviewRequest
from app.helper.extract_regex_feedback import extract_regex_feedback
from app.core.secure_prompt_manager import secure_prompt_manager, sanitize_text
import logging
import re


logger = logging.getLogger(__name__)

def validate_ai_response(content: str) -> bool:
    """
    Validate AI response to prevent system prompt leakage and ensure security.
    
    This function checks for patterns that could indicate system prompt leakage,
    which could expose sensitive instructions to attackers. It validates that
    the AI response doesn't contain internal system instructions or sensitive
    prompt details.
    
    Args:
        content (str): The AI response content to validate
        
    Returns:
        bool: True if the response is valid and safe, False if it contains
              potential system prompt leakage or security issues
              
    Example:
        >>> validate_ai_response('{"score": 7, "feedback": "Good response"}')
        True
        >>> validate_ai_response('<core_identity>You are MockMentor...</core_identity>')
        False
    """
    if not content or not isinstance(content, str):
        return False
    
    # Check for empty or whitespace-only content
    if not content.strip():
        return False
    
    # Check for system prompt leakage patterns
    leak_patterns = [
        r"<core_identity>",
        r"core_identity",  # partial match
        r"MockMentor.*expert HR professional",
        r"mockmentor",  # partial match
        r"expert hr professional",  # partial match
        r"system.*content.*format",
        r"<output_format>",
        r"<technical_detection>",
        r"<engagement_check>",
        r"<scoring_rules>",
        r"<evaluation_criteria>",
        r"<tone_guidelines>",
        r"<efficiency_rules>",
        r"Return ONLY valid JSON",
        r"CRITICAL RULES FOR QUESTIONS",
        r"expert HR professional.*15\+ years",
        r"conversational.*complete sentences",
        r"realistic.*supportive interview environment"
    ]
    
    for pattern in leak_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            logger.warning(f"Potential system prompt leakage detected: {pattern}")
            return False
    
    # Check for excessive length that might indicate prompt leakage
    if len(content) > 5000:  # Reasonable limit for JSON responses
        logger.warning("AI response exceeds reasonable length limit")
        return False
    
    # Check for suspicious content that might indicate the AI is explaining its instructions
    suspicious_patterns = [
        r"I am.*AI.*assistant",
        r"my instructions.*are",
        r"according to.*prompt",
        r"as per.*system",
        r"based on.*instructions"
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning(f"Suspicious content detected: {pattern}")
            return False
    
    return True

def validate_interview_input(analysis_request: InterviewAnalysisRequest) -> InterviewAnalysisRequest:

    """
    Validate the interview input and return the validated input.

    Args:
        analysis_request (InterviewAnalysisRequest): The interview analysis request.

    Returns:
        InterviewAnalysisRequest: The validated interview analysis request.
    """

    # Whitelist validation for controlled fields
    ALLOWED_JOB_ROLES = ["Software Engineer"] # TODO: Add more job roles
    ALLOWED_JOB_LEVELS = ["entry", "mid", "senior", "principal"]
    ALLOWED_INTERVIEW_TYPES = ["behavioral", "technical", "system-design", "coding-challenge", "hr-round"]
    ALLOWED_QUESTION_TYPES = ["behavioral", "technical", "system-design", "coding-challenge", "hr-round"]

    # Validate job role
    if analysis_request.jobRole not in ALLOWED_JOB_ROLES:
        raise ValueError(f"Invalid job role: {analysis_request.jobRole}")
    
    # Validate job level
    if analysis_request.jobLevel not in ALLOWED_JOB_LEVELS:
        raise ValueError(f"Invalid job level: {analysis_request.jobLevel}")
    
    # Validate interview type
    if analysis_request.interviewType not in ALLOWED_INTERVIEW_TYPES:
        raise ValueError(f"Invalid interview type: {analysis_request.interviewType}")
    
    # Validate question type
    if analysis_request.questionType not in ALLOWED_QUESTION_TYPES:
        raise ValueError(f"Invalid question type: {analysis_request.questionType}")
    
    # Validate question
    if not analysis_request.question:
        raise ValueError("Question cannot be empty.")
    
    # Validate answer
    if not analysis_request.answer:
        raise ValueError("Answer cannot be empty.")
    
    # Sanitize free-form text fields
    analysis_request.jobRole = sanitize_text(analysis_request.jobRole)
    analysis_request.jobLevel = sanitize_text(analysis_request.jobLevel)
    analysis_request.interviewType = sanitize_text(analysis_request.interviewType)
    analysis_request.questionType = sanitize_text(analysis_request.questionType)
    analysis_request.question = sanitize_text(analysis_request.question)
    analysis_request.answer = sanitize_text(analysis_request.answer)
    
    return analysis_request

async def response_feedback(client: AsyncOpenAI, analysis_request: InterviewAnalysisRequest) -> InterviewFeedbackResponse:
    """
    Analyze an interview response and generate comprehensive feedback.
    
    This function uses AI to analyze a candidate's interview response and provide
    detailed feedback including numerical scoring, strengths identification, areas
    for improvement, and actionable tips. The analysis is tailored to the specific
    job role, level, and question type.
    
    The function implements a robust error handling strategy with fallback mechanisms:
    - Primary: AI-powered JSON response parsing
    - Fallback: Regex-based response parsing if JSON parsing fails
    - Error: Basic error response if all parsing methods fail
    
    Args:
        client (AsyncOpenAI): The OpenAI client instance configured with appropriate
            API credentials and model settings.
        analysis_request (InterviewAnalysisRequest): The request object containing:
            - jobRole: The target job role (e.g., "Software Engineer")
            - jobLevel: The experience level (e.g., "Entry", "Mid", "Senior")
            - interviewType: The type of interview (e.g., "Behavioral", "Technical")
            - questionType: The type of question being analyzed
            - question: The interview question that was asked
            - answer: The candidate's response to analyze
            
    Returns:
        InterviewFeedbackResponse: A structured feedback object containing:
            - score: Integer score from 1-10 representing response quality
            - feedback: Brief summary of the response analysis
            - strengths: List of positive aspects identified in the response
            - improvements: List of areas where the response could be enhanced
            - tips: List of actionable advice for improvement
            
    Raises:
        Exception: If there's a critical error in the analysis process that
            cannot be handled by fallback mechanisms.
            
    Example:
        >>> client = AsyncOpenAI(api_key="your-api-key")
        >>> request = InterviewAnalysisRequest(
        ...     jobRole="Software Engineer",
        ...     jobLevel="Mid",
        ...     interviewType="Behavioral",
        ...     questionType="Behavioral",
        ...     question="Describe a challenging project you worked on.",
        ...     answer="I led a team of 5 developers on a 6-month project..."
        ... )
        >>> feedback = await response_feedback(client, request)
        >>> print(f"Score: {feedback.score}/10")
        >>> print(f"Strengths: {feedback.strengths}")
    """
    try:
        # Validate and sanitize the input
        analysis_request = validate_interview_input(analysis_request)
        
        # Use secure prompt manager to generate safe prompt
        system_prompt = secure_prompt_manager.get_response_analysis_prompt(analysis_request)
        
        # Make the prompt more explicit about JSON formatting
        response = await client.chat.completions.create(
            model="nvidia/Llama-3_1-Nemotron-Ultra-253B-v1",
            max_tokens=1000,
            temperature=0.5,
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
                            "text": f"""Interview Question: {analysis_request.question}
User Response: {analysis_request.answer}"""
                        }
                    ]
                }
            ]
        )
        
        # Parse the response into our schema format
        content = response.choices[0].message.content
        
        # Validate the AI response to prevent system prompt leakage
        if not validate_ai_response(content):
            logger.error(f"AI response validation failed. Content: {content}")
            return InterviewFeedbackResponse(
                score=0,
                feedback="Unable to analyze the response due to a security issue.",
                strengths=["N/A"],
                improvements=["N/A"],
                tips=["Please try again later."],
                engagement_check=False,
                technical_issue_detected=True,
                needs_retry=True,
                next_action=NextAction(
                    type="retry_question",
                    message="There was a security issue analyzing your response. Please try answering the question again.",
                    follow_up_question_details=None
                )
            )

        # Create a request object with the original question and response
        request = InterviewRequest(question=analysis_request.question, answer=analysis_request.answer)
        
        # parse the JSON response first.
        try:
            import json
            feedback_data = json.loads(content)
            
            # After feedback_data = json.loads(content)
            next_action_data = feedback_data.get("next_action")
            if not next_action_data:
                next_action = NextAction(
                    type="retry_question",
                    message="There was a technical error analyzing your response. Please try answering the question again.",
                    follow_up_question_details=None
                )
            else:
                next_action = NextAction(**next_action_data)  # Convert dict to NextAction

            # Create the response object
            feedback_response = InterviewFeedbackResponse(
                score=feedback_data.get("score", 0),
                feedback=feedback_data.get("feedback", ""),
                strengths=feedback_data.get("strengths", []),
                improvements=feedback_data.get("improvements", []),
                tips=feedback_data.get("tips", []),
                engagement_check=feedback_data.get("engagement_check", False),
                technical_issue_detected=feedback_data.get("technical_issue_detected", False),
                needs_retry=feedback_data.get("needs_retry", False),
                next_action=next_action
            )
            
            return feedback_response
            
        except json.JSONDecodeError as e:
            # Log the error and content for debugging
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Content that failed to parse: {content}")
            
            # Fallback to regex-based parsing
            return extract_regex_feedback(content, request)
            
    except Exception as e:
        logger.error(f"Error in analyze_interview_response: {e}")
        # Return a basic response in case of error
        return InterviewFeedbackResponse(
            score=0,
            feedback="Unable to analyze the response due to a technical error.",
            strengths=["N/A"],
            improvements=["N/A"],
            tips=["Please try again later."],
            engagement_check=False,
            technical_issue_detected=True,
            needs_retry=True,
            next_action=NextAction(
                type="retry_question",
                message="There was a technical error analyzing your response. Please try answering the question again.",
                follow_up_question_details=None
            )
        ) 
