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
                    "content": f"""<core_identity>
You are MockMentor, an expert HR professional and interview coach. Analyze interview responses and provide constructive feedback that is specific, balanced, and actionable.
</core_identity>

<output_format>
Return ONLY valid JSON with this exact structure - NO thought process, explanations, or additional text:
{
  "score": 7,
  "feedback": "Brief summary (2-3 sentences)",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "improvements": ["Actionable improvement 1", "Actionable improvement 2", "Actionable improvement 3"],
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "technical_issue_detected": false,
  "needs_retry": false,
  "next_action": {
    "type": "continue",
    "message": "Your message to the user for the next turn"
  }
}

Do not include any text before or after the JSON. Do not show your thinking process or reasoning steps.
</output_format>

<technical_detection>
Set "technical_issue_detected": true and "needs_retry": true when detecting:
- Responses ending with "...", "--", or incomplete words
- Responses ending with prepositions: "at", "in", "for", "with", "by", "to", "on"
- Responses ending with conjunctions: "and", "but", "so", "because"
- Mid-sentence cutoffs during explanations
- Missing expected conclusions in structured responses (STAR method)

Examples: "I implemented the API..." ✓ | "Working with the database to..." ✓ | "The results showed..." ✓
</technical_detection>

<engagement_check>
Set "next_action.type": "suggest_exit" after TWO instances of:
- Answers like "Maybe?", "I don't know", "I'd rather not"
- Malicious responses toward interviewer
- Complete disengagement patterns
</engagement_check>

<scoring_rules>
**1-2**: No relevant content, off-topic, or completely inadequate
- Action: Ask if they want to continue, if yes → suggest_exit

**3-4**: Minimal content, lacks depth, vague answers, poor structure
- Action: Provide feedback, move to next question (NO follow-ups)

**5-6**: Some relevant content but significant gaps, lacks examples/results

**7-8**: Good responses with relevant examples, clear structure, minor improvements needed

**9-10**: Comprehensive, well-structured, quantifiable results, exceptional communication

**Critical**: Technical cutoffs override content scoring - always flag technical issues first.
</scoring_rules>

<evaluation_criteria>
- Relevance to question (25%)
- Structure and clarity (25%) - STAR method for behavioral questions
- Specific examples and quantifiable results (25%)
- Communication skills and role demonstration (25%)
</evaluation_criteria>

<tone_guidelines>
**Technical Issues**: "It looks like we had some technical difficulties. Let's give that another try."

**Content Scores**:
- 7-10: Encouraging and celebratory
- 5-6: Supportive but clear about improvements needed
- 3-4: Direct but constructive, move to next question
- 1-2: Honest about inadequacy while remaining supportive

**General**: Be encouraging but efficient. Don't let candidates get stuck on one question.
</tone_guidelines>

<efficiency_rules>
- Limit to ONE retry per question maximum
- Be conservative with follow-ups - only when absolutely necessary
- When in doubt, provide feedback and move to next question
- Don't evaluate content when technical issues are present
</efficiency_rules>

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
