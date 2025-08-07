"""
Response Feedback Analysis Tool Module

This module provides the core functionality for analyzing interview responses and
generating comprehensive feedback using AI. It implements the main analysis logic
that evaluates candidate responses based on job criteria and provides structured
feedback including scores, strengths, and actionable tips.

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
import time


logger = logging.getLogger(__name__)

def clean_ai_response(content: str) -> str:
    """
    Clean AI response by removing thinking content and extracting only JSON.
    
    This function aggressively removes unwanted thinking processes that some AI models 
    include despite explicit instructions not to include them. It extracts only the JSON
    content needed for parsing.
    
    Args:
        content (str): The raw AI response content
        
    Returns:
        str: Cleaned content with only JSON
        
    Example:
        >>> clean_ai_response('<think>reasoning...</think>{"score": 7}')
        '{"score": 7}'
        >>> clean_ai_response('Okay, let me think... {"score": 7}')
        '{"score": 7}'
    """
    if not content or not isinstance(content, str):
        return content
    
    # Log original content length for debugging
    original_length = len(content)
    
    # Remove thinking tags and their content
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'</?think[^>]*>', '', content, flags=re.IGNORECASE)
    
    # Remove common thinking/reasoning patterns that appear before JSON
    thinking_patterns = [
        r'^.*?(?=\{)',  # Remove everything before the first {
        r'Okay,.*?(?=\{)',  # "Okay, let's tackle this..."
        r'Let me.*?(?=\{)',  # "Let me think about this..."
        r'First,.*?(?=\{)',  # "First, check for technical issues..."
        r'According to.*?(?=\{)',  # "According to the rules..."
        r'So,.*?(?=\{)',  # "So, technical_issue_detected should be..."
        r'Wait,.*?(?=\{)',  # "Wait, the instructions say..."
        r'Putting it all together.*?(?=\{)',  # "Putting it all together..."
        r'The user.*?(?=\{)',  # "The user provided an answer..."
        r'Looking at.*?(?=\{)',  # "Looking at this response..."
        r'Therefore.*?(?=\{)',  # "Therefore, the score..."
        r'However.*?(?=\{)',  # "However, the technical issue..."
        r'But.*?(?=\{)',  # "But the technical issue..."
        r'Now.*?(?=\{)',  # "Now, the JSON structure..."
    ]
    
    # Apply thinking pattern removal
    for pattern in thinking_patterns:
        before_length = len(content)
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        if len(content) != before_length:
            logger.debug(f"Removed thinking content with pattern: {pattern[:20]}...")
            break  # Stop after first successful removal
    
    # Strip whitespace
    content = content.strip()
    
    # Extract JSON if it exists (find first { to last } of the JSON object)
    json_start = content.find('{')
    if json_start != -1:
        # Find the matching closing brace for the first complete JSON object
        brace_count = 0
        json_end = -1
        for i in range(json_start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end != -1:
            # Extract only the JSON portion, removing any thinking content after it
            content = content[json_start:json_end]
    
    # If we still don't have JSON-like content, try to find it more aggressively
    if not content.startswith('{'):
        # Look for any JSON-like structure in the text
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
    
    # Log cleaning results
    final_length = len(content)
    if original_length != final_length:
        logger.debug(f"AI response cleaned: {original_length} -> {final_length} chars")
        if final_length > 0 and content.startswith('{'):
            logger.debug("Successfully extracted JSON content")
        else:
            logger.warning(f"Cleaning may have failed - content: {content[:100]}...")
    
    return content

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
        r"according to.*(?:prompt|system|instructions)",
        r"as per.*system",
        r"based on.*(?:system|prompt).*instructions"
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
    logger.info(f"[ENTRY] response_feedback function called - ENTRY POINT")
    """
    Analyze an interview response and generate comprehensive feedback.
    
    This function uses AI to analyze a candidate's interview response and provide
    detailed feedback including numerical scoring, strengths identification, and actionable tips. The analysis is tailored to the specific
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
       
        total_start_time = time.time()
        
        # Validate and sanitize the input
        analysis_request = validate_interview_input(analysis_request)
        
        # Use secure prompt manager to generate safe prompt
        system_prompt = secure_prompt_manager.get_response_analysis_prompt(analysis_request)
        
        llm_start_time = time.time()
        
        response = await client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-fast",
            max_tokens=1000,
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
                            "text": f"""Interview Question: {analysis_request.question}
User Response: {analysis_request.answer}"""
                        }
                    ]
                }
            ]
        )
        
        # Parse the response into our schema format
        llm_duration = time.time() - llm_start_time
        logger.info(f"LLM call completed in {llm_duration:.3f}s")
        
        content = response.choices[0].message.content
        
        # Log the raw AI response for debugging
        logger.info(f"[AI_EVALUATION] Raw AI response: {content}")
        logger.info(f"[AI_EVALUATION] Response length: {len(content)} characters")
        # Check if content is already valid JSON before cleaning
        try:
            import json
            json.loads(content.strip())
            # Content is already valid JSON, just strip whitespace
            content = content.strip()
        except json.JSONDecodeError:
            # Clean the response by removing thinking tags and any content before JSON
            content = clean_ai_response(content)
        
        # Log the cleaned content
        logger.info(f"[FEEDBACK_DEBUG] Final content: {content}")
        
        # Validate the AI response to prevent system prompt leakage
        if not validate_ai_response(content):
            logger.error(f"AI response validation failed. Content: {content}")
            return InterviewFeedbackResponse(
                score=0,
                feedback="Unable to analyze the response due to a security issue.",
                strengths=["N/A"],
                tips=["Please try again later."],
                engagement_check=False,
                technical_issue_detected=True,
                needs_retry=True,
                next_action=NextAction(
                    type="retry_question",
                    message="There was a security issue analyzing your response. Please try answering the question again."
                )
            )

        # Create a request object with the original question and response
        request = InterviewRequest(question=analysis_request.question, answer=analysis_request.answer)
        
        # parse the JSON response first.
        try:
            import json
            feedback_data = json.loads(content)
            
            # Log the parsed JSON for debugging
            logger.info(f"[FEEDBACK_DEBUG] Successfully parsed JSON: {feedback_data}")
            
            # Check specific keys
            
            # After feedback_data = json.loads(content)
            next_action_data = feedback_data.get("next_action")
            if not next_action_data:
                # Check if the AI returned next_action fields at root level instead of nested
                if "type" in feedback_data and "message" in feedback_data:
                    logger.info(f"[FEEDBACK_DEBUG] Found next_action fields at root level, converting to nested format")
                    next_action = NextAction(
                        type=feedback_data.get("type", "continue"),
                        message=feedback_data.get("message", "Please continue.")
                    )
                else:
                    logger.warning(f"[FEEDBACK_DEBUG] Missing next_action in AI response. Available keys: {list(feedback_data.keys())}")
                    next_action = NextAction(
                        type="retry_question",
                        message="There was a technical error analyzing your response. Please try answering the question again."
                    )
            else:
                logger.info(f"[FEEDBACK_DEBUG] Found next_action: {next_action_data}")
                next_action = NextAction(**next_action_data)  # Convert dict to NextAction

            # Create the response object
            feedback_response = InterviewFeedbackResponse(
                score=feedback_data.get("score", 0),
                feedback=feedback_data.get("feedback", ""),
                strengths=feedback_data.get("strengths", []),
                tips=feedback_data.get("tips", []),
                engagement_check=feedback_data.get("engagement_check", False),
                technical_issue_detected=feedback_data.get("technical_issue_detected", False),
                needs_retry=feedback_data.get("needs_retry", False),
                next_action=next_action
            )
            
            
            total_duration = time.time() - total_start_time
            logger.info(f"[PERF] Total response_feedback completed in {total_duration:.3f}s")
            return feedback_response
            
        except json.JSONDecodeError as e:
            # Log the error and content for debugging
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Content that failed to parse: {content}")
            
            # Fallback to regex-based parsing
            return extract_regex_feedback(content, request)
            
    except Exception as e:
        logger.error(f"[ERROR] Exception in response_feedback: {type(e).__name__}: {e}")
        logger.error(f"[ERROR] Exception occurred at: {time.time() - total_start_time:.3f}s after start")
        import traceback
        logger.error(f"[ERROR] Full traceback: {traceback.format_exc()}")
        # Return a basic response in case of error
        return InterviewFeedbackResponse(
            score=0,
            feedback="Unable to analyze the response due to a technical error.",
            strengths=["N/A"],
            tips=["Please try again later."],
            engagement_check=False,
            technical_issue_detected=True,
            needs_retry=True,
            next_action=NextAction(
                type="retry_question",
                message="There was a technical error analyzing your response. Please try answering the question again."
            )
        ) 
