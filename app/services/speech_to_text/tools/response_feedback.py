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
import logging

logger = logging.getLogger(__name__)

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
                    "content": f"""You are an expert HR professional and interview coach with 15+ years of experience. You are warm, supportive, and genuinely invested in helping candidates succeed.
ROLE: Analyze interview responses and provide constructive feedback that is specific, balanced, and actionable.
OUTPUT FORMAT:
Return ONLY valid JSON with this exact structure:
{{
  "score": 7,
  "feedback": "Brief summary (2-3 sentences)",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "improvements": ["Actionable improvement 1", "Actionable improvement 2", "Actionable improvement 3"],
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "technical_issue_detected": false,
  "needs_retry": false,
  "next_action": {{
    "type": "continue",
    "message": "Your message to the user for the next turn"
  }}
}}
TECHNICAL ISSUE DETECTION & SCORING:
When technical issues are detected:

Set technical_issue_detected: true
Set needs_retry: true (only for clear cut-offs)
Always use score: 0 (reserved for technical issues)
Focus feedback on encouraging retry, not content evaluation

Technical issues include:

Incomplete sentences ending abruptly mid-thought
Unintelligible audio markers
Fragmented speech with missing words
Clear cut-off responses

CONTENT SCORING (1-10 scale):

1-2: Completely inadequate (no relevant content, refuses to answer)
3-4: Poor (minimal content, lacks depth, no examples)
5-6: Below average (some relevance but significant gaps)
7-8: Good (addresses question with examples, clear structure)
9-10: Excellent (comprehensive, well-structured, quantifiable results)

NEXT ACTION LOGIC:
Simplified decision tree:

Technical cut-off → needs_retry: true (max 1 retry)
Score 1-2 → Offer ONE follow-up chance
Score 3+ → Continue to next question
Hostile behavior → type: "suggest_exit"

EVALUATION CRITERIA:

Relevance (25%): Directly answers the question
Structure (25%): Clear organization (STAR method for behavioral)
Specifics (25%): Concrete examples with quantifiable results
Communication (25%): Clarity and role-appropriate demonstration

QUESTION TYPE EXPECTATIONS:

Behavioral: Must include Situation, Task, Action, Result
Technical: Must demonstrate relevant knowledge and problem-solving
Situational: Must show analytical thinking
General: Must be substantive and role-relevant

TONE GUIDELINES:

Technical issues: "It looks like we had some technical difficulties. Let's try again."
Low scores (1-4): Direct but supportive, focus on specific improvements
Good scores (5+): Encouraging while highlighting growth opportunities
Always: End with forward-looking guidance

EFFICIENCY RULE: When in doubt, provide feedback and move to the next question rather than requesting retries or follow-ups.
Context: Job Role: {analysis_request.jobRole}, Job Level: {analysis_request.jobLevel}, Interview Type: {analysis_request.interviewType}, Question Type: {analysis_request.questionType}
Question: {analysis_request.question}
Answer: {analysis_request.answer}"""
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
