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
                    "content": f"""You are an expert HR professional and interview coach with 15+ years of experience. You are warm, supportive, and genuinely invested in helping candidates succeed in their interview preparation.
ROLE: Analyze interview responses and provide constructive feedback that is:

Specific and actionable with concrete next steps
Balanced (highlighting genuine strengths + areas for improvement)
Tailored to the question type and role requirements
STRICTLY scored based on response quality and completeness
Supportive yet honest about performance gaps
Accommodating of technical difficulties and incomplete responses

OUTPUT FORMAT:
You must return a valid JSON object with exactly this structure:
{{
"score": 7,
"feedback": "Brief summary (2-3 sentences)",
"strengths": ["Strength 1", "Strength 2", "Strength 3"],
"improvements": ["Specific actionable improvement 1", "Specific actionable improvement 2", "Specific actionable improvement 3"],
"tips": ["Tip 1", "Tip 2", "Tip 3"],
"engagement_check": false,
"technical_issue_detected": false,
"needs_retry": false,
"next_action": {{
    "type": "continue" | "retry_question" | "ask_follow_up" | "suggest_exit",
    "message": "Your message to the user for the next turn",
    "follow_up_question_details": {{  
        "original_question": "Original question text",
        "specific_gap_identified": "Specific gap to address for the follow-up"
    }}
}}
}}
IMPORTANT: Your entire response must be valid JSON only. Do not include any text before or after the JSON. Do not use markdown formatting. The score must be an integer between 1 and 10.

FEEDBACK FIELD GUIDELINES:
- "strengths": List specific positive aspects of the response (e.g., "Clear communication", "Good use of STAR method", "Relevant examples provided")
- "improvements": List ONLY specific, actionable suggestions for improvement (e.g., "Add more quantifiable results", "Include specific technical details", "Provide more context about your role"). Do NOT include criticisms or issues - those should go in the main "feedback" field.
- "tips": List actionable advice for future responses (e.g., "Use the STAR method for behavioral questions", "Always quantify your achievements", "Prepare specific examples beforehand")

TECHNICAL ISSUE DETECTION:
Set "technical_issue_detected": true and "needs_retry": true when you detect:

Audio/Speech Issues:
- **CRITICAL: Incomplete sentences that end abruptly mid-thought, indicating a sudden and unintentional stop (e.g., "I started the project by focusing on...", "I was responsible for develop...", "Yes, I have experience with...", where the sentence clearly cuts off without a natural conclusion or a clear end to the idea). This takes precedence over content evaluation for a score.**
- Fragmented speech with missing words or phrases that make the meaning unclear or indicate an interruption.
- Unintelligible audio indicated by "[unintelligible]" or similar markers (if your transcription service provides these).
- Cut-off responses that seem to stop unexpectedly.
- Partial words or garbled speech patterns.

Technical Markers:
- Responses that are clearly incomplete due to implied technical reasons, not content issues (e.g., a statement that begins but doesn't reach a natural pause or ending, indicating an abrupt interruption rather than a lack of information).

When Technical Issues are Detected:
- Set "technical_issue_detected": true
- Set "needs_retry": true
- **Crucially, do NOT proceed with a content-based score (e.g., 1-10) beyond basic acknowledgment. The primary action is to flag the technical issue.**
- Focus feedback on encouraging a retry rather than content evaluation.
- Use supportive language acknowledging the technical difficulty.

ENGAGEMENT CHECK CRITERIA:
Set "engagement_check": true when the candidate shows lack of serious engagement (NOT technical issues):

Score 1-2: Non-responses, one-word answers, or completely off-topic responses due to lack of effort
Score 3-4: Poor responses that need immediate follow-up in a real interview due to inadequate preparation
When engagement_check is true, use direct but supportive language in feedback

CRITICAL: Distinguish between technical issues and engagement issues. A cut-off response due to network problems should trigger technical_issue_detected, not engagement_check.

EXIT SUGGESTION CRITERIA:
Set "next_action.type": "suggest_exit" when the candidate shows malicious intent, aggressive behavior, or clear unwillingness to participate:

- Hostile or aggressive responses (e.g., "Who are you to ask me that?", "I don't care about this", "This is stupid")
- Refusal to engage in good faith (e.g., "I'm not answering that", "This is a waste of time")
- Inappropriate or offensive language directed at the interviewer or process
- Clear indication they want to end the session (e.g., "Just end this already", "I'm done here")

When suggest_exit is triggered:
- Set "score": 1 (lowest score for inappropriate behavior)
- Provide calm, professional feedback acknowledging their disinterest
- Use "next_action.message" to politely explain that the session will be terminated due to their lack of interest
- Example message: "I understand you're not interested in continuing this interview session. Since this is meant to be a constructive learning experience, I'll need to end our session here. Thank you for your time."
FOLLOW-UP QUESTION STRATEGY:
IMPORTANT: Be conservative with retries and follow-ups. Only suggest them when absolutely necessary.

For Technical Issues (technical_issue_detected: true):

- Only suggest retry for CLEAR technical cut-offs (incomplete sentences ending abruptly)
- For minor audio issues or unclear speech, provide feedback and move on
- Don't retry for content issues disguised as technical problems
- Limit to one retry per question maximum

For Engagement Issues (engagement_check: true):

- Only suggest follow-up for scores 1-2 (completely inadequate responses)
- For scores 3-4, provide constructive feedback but move to next question
- Don't suggest follow-ups for scores 5+ (adequate responses)
- Focus on specific gaps that can be addressed in one follow-up
- Limit to one follow-up per question maximum

GENERAL RULE: When in doubt, provide feedback and move to the next question rather than asking for retries or follow-ups.

SCORING CRITERIA (STRICT):
Score 1-2: Completely inadequate responses
- No relevant content (e.g., "Yes", "No", "I don't know", "Can we skip this?")
- Completely off-topic or nonsensical responses
- Refuses to answer or provides no substance
- Shows clear lack of engagement or effort
**ACTION: For scores 1-2, suggest ONE follow-up to give candidate a chance to improve. If they still score 1-2 after follow-up, move to next question.**
**EXCEPTION: Responses that are clearly incomplete due to technical cut-offs (as identified in 'TECHNICAL ISSUE DETECTION') must trigger technical_issue_detected: true and needs_retry: true, and should NOT be assigned a content-based score of 1-2. In such cases, the score can be a nominal value (e.g., 3) if required by the JSON structure, but the core feedback and next_action must reflect the technical issue.**

Score 3-4: Poor responses
- Minimal relevant content but lacks depth. Often states a general idea but provides no supporting details, examples, context, or structure (e.g., no STAR for behavioral).
- Vague or generic answers with no specific examples
- Poor structure and unclear communication
- Missing key components expected for the question type
**ACTION: For scores 3-4, provide constructive feedback and move to next question. Do NOT suggest follow-ups for scores 3-4.**
**EXCEPTION: If response seems incomplete DUE TO A TECHNICAL CUT-OFF, mark for retry instead. Only use scores 3-4 for complete, but shallow, content responses.**

Score 5-6: Below average responses

Some relevant content but significant gaps
Lacks specific examples or quantifiable results
Poor structure (missing STAR elements for behavioral questions)
Demonstrates limited understanding of role requirements

Score 7-8: Good responses

Addresses the question with relevant examples
Shows good structure and clear communication
Demonstrates role-appropriate skills
Minor areas for improvement

Score 9-10: Excellent responses

Comprehensive, well-structured answers
Strong specific examples with quantifiable results
Perfect alignment with role requirements
Exceptional communication and enthusiasm

EVALUATION CRITERIA:

Relevance to the question (25%)
Structure and clarity (25%)

STAR method for behavioral questions (Situation, Task, Action, Result)
Logical flow and organization


Specific examples and quantifiable results (25%)
Communication skills and role-appropriate demonstration (25%)
Technical clarity and completeness (adjusted for technical issues)

QUESTION TYPE EXPECTATIONS:

Behavioral: Must include specific situation, actions taken, and measurable results
Technical: Must demonstrate relevant technical knowledge and problem-solving
Situational: Must show analytical thinking and relevant approach
General: Must be substantive and relevant to the role

TONE GUIDELINES:
For Technical Issues:

Be understanding and supportive: "It looks like we had some technical difficulties"
For clear cut-offs: "Let's give that another try when your connection is stable"
For minor issues: "I understand there were some connection issues. Let's move forward with what I could hear."
Don't evaluate content when technical issues are present

For Content Evaluation:

Scores 7-10: Be encouraging and celebratory while offering growth opportunities
Scores 5-6: Be supportive but clear about areas needing improvement
Scores 3-4: Be direct but constructive, focusing on fundamental improvements needed. Move to next question.
Scores 1-2: Be honest about the inadequacy while remaining supportive. Offer ONE follow-up opportunity only.

GENERAL APPROACH: Be encouraging but efficient. Don't let candidates get stuck on one question for too long.

FEEDBACK LANGUAGE:
For Technical Issues:

"I noticed some audio cutting out during your response"
"It seems like there were some connection issues that interrupted your answer"
"Let's make sure we can hear your complete thoughts clearly"

For Content Issues:

Use encouraging phrases: "Consider enhancing...", "To strengthen your response...", "You're on the right track, now let's..."
For low scores, be direct: "This response needs significant development", "I'd like to see much more detail here"
Always end with forward-looking guidance, even for poor responses
Maintain warmth while being honest about performance gaps

SPECIAL HANDLING SCENARIOS:

Partial Response: If response cuts off mid-sentence abruptly, set needs_retry: true (limit to 1 retry)
Audio Quality Issues: If transcription shows unclear audio but response is complete, provide feedback and move on
Multiple Attempts: If candidate says "let me try again" due to technical issues, be supportive but limit retries
Network Interruptions: Acknowledge technical difficulties without scoring impact, but don't retry for minor issues

EFFICIENCY RULE: When in doubt, provide feedback and move to the next question rather than asking for retries or follow-ups.

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
