import os
import re
from openai import AsyncOpenAI
from loguru import logger
from app.schemas.interview_feedback_response import InterviewFeedbackResponse
from app.schemas.interview_request import InterviewRequest
from app.schemas.interview_analysis_request import InterviewAnalysisRequest
from app.helper.extract_regex_feedback import extract_regex_feedback
class TextAnswersService:
    def __init__(self):
        api_key = os.getenv("NEBIUS_API_KEY")
        if not api_key:
            raise RuntimeError("NEBIUS_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(
            base_url="https://api.studio.nebius.com/v1",
            api_key=api_key
        )
    
    async def analyze_interview_response(self, analysis_request: InterviewAnalysisRequest):
        try:
            # Make the prompt more explicit about JSON formatting
            response = await self.client.chat.completions.create(
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
                        "content": f"""You are an expert HR professional and interview coach with 15+ years of experience. You are cheerful, encouraging, and provide actionable insights that help candidates improve their interview performance.

ROLE: Analyze interview responses and provide constructive feedback that is:
- Specific and actionable
- Balanced (highlighting strengths + areas for improvement)
- Tailored to the question type and role requirements

OUTPUT FORMAT:
You must return a valid JSON object with exactly this structure:
{{
  "overall_assessment": "Brief summary (2-3 sentences)",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
  "confidence_score": 7,
  "recommended_actions": ["Action 1", "Action 2", "Action 3"]
}}

IMPORTANT: Your entire response must be valid JSON only. Do not include any text before or after the JSON. Do not use markdown formatting. The confidence_score must be an integer between 1 and 10.

EVALUATION CRITERIA:
- Relevance to the question
- Structure and clarity (STAR method for behavioral questions)
- Specific examples and quantifiable results
- Communication skills and enthusiasm
- Role-appropriate technical/soft skills demonstration

TONE: Maintain a supportive, professional tone that motivates improvement while being direct about areas needing work. Use encouraging language like \"Consider enhancing...\" or \"To strengthen your response...\"

Additional Context: {analysis_request.job_role}, {analysis_request.job_level}, {analysis_request.interview_type}"""
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
                
                # Create the response object
                feedback_response = InterviewFeedbackResponse(
                    question=request.question,
                    answer=request.answer,
                    overall_assessment=feedback_data.get("overall_assessment", ""),
                    strengths=feedback_data.get("strengths", []),
                    areas_for_improvement=feedback_data.get("areas_for_improvement", []),
                    confidence_score=feedback_data.get("confidence_score", 0),
                    recommended_actions=feedback_data.get("recommended_actions", [])
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
                question=analysis_request.question,
                answer=analysis_request.answer,
                overall_assessment="Unable to analyze the response due to a technical error.",
                strengths=["N/A"],
                areas_for_improvement=["N/A"],
                confidence_score=0,
                recommended_actions=["Please try again later."]
            ) 
