from openai import AsyncOpenAI
from loguru import logger
from app.schemas.text_schemas.interview_feedback_response import InterviewFeedbackResponse
from app.schemas.text_schemas.interview_request import InterviewRequest
from app.schemas.text_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.helper.extract_regex_feedback import extract_regex_feedback

class TextAnswersService:
    """
    Service class for analyzing interview responses and providing feedback.
    """
    
    def __init__(self, client: AsyncOpenAI):
        """
        Initialize the service with an OpenAI client.
        
        Args:
            client (AsyncOpenAI): The OpenAI client instance.
        """
        self.client = client
    
    async def analyze_response(self, analysis_request: InterviewAnalysisRequest) -> InterviewFeedbackResponse:
        """
        Analyze an interview response and provide feedback.
        
        Args:
            analysis_request (InterviewAnalysisRequest): The request containing the interview details and response.
            
        Returns:
            InterviewFeedbackResponse: The analysis results including score, feedback, strengths, and improvements.
        """
        return await analyze_interview_response(self.client, analysis_request)

async def analyze_interview_response(client: AsyncOpenAI, analysis_request: InterviewAnalysisRequest) -> InterviewFeedbackResponse:
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
                        "content": f"""You are an expert HR professional and interview coach with 15+ years of experience. You are cheerful, encouraging, and provide actionable insights that help candidates improve their interview performance.

ROLE: Analyze interview responses and provide constructive feedback that is:
- Specific and actionable
- Balanced (highlighting strengths + areas for improvement)
- Tailored to the question type and role requirements

OUTPUT FORMAT:
You must return a valid JSON object with exactly this structure:
{{
  "score": 7,
  "feedback": "Brief summary (2-3 sentences)",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "improvements": ["Area 1", "Area 2", "Area 3"],
  "tips": ["Tip 1", "Tip 2", "Tip 3"]
}}

IMPORTANT: Your entire response must be valid JSON only. Do not include any text before or after the JSON. Do not use markdown formatting. The score must be an integer between 1 and 10.

EVALUATION CRITERIA:
- Relevance to the question
- Structure and clarity (STAR method for behavioral questions)
- Specific examples and quantifiable results
- Communication skills and enthusiasm
- Role-appropriate technical/soft skills demonstration

TONE: Maintain a supportive, professional tone that motivates improvement while being direct about areas needing work. Use encouraging language like \"Consider enhancing...\" or \"To strengthen your response...\"

Additional Context: {analysis_request.jobRole}, {analysis_request.jobLevel}, {analysis_request.interviewType}, {analysis_request.questionType}"""
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
                    score=feedback_data.get("score", 0),
                    feedback=feedback_data.get("feedback", ""),
                    strengths=feedback_data.get("strengths", []),
                    improvements=feedback_data.get("improvements", []),
                    tips=feedback_data.get("tips", [])
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
                tips=["Please try again later."]
            ) 
