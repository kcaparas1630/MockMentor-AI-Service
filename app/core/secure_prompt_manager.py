"""
Secure Prompt Manager Module

This module provides a secure way to manage AI prompts by isolating them from user data
to prevent injection attacks. It implements a template-based system with explicit
placeholders and comprehensive sanitization.

The module contains:
- PromptTemplate: A dataclass for secure prompt templates with placeholders
- SecurePromptManager: Main class for managing secure prompts
- sanitize_text: Utility function for text sanitization

Dependencies:
- dataclasses: For template data structures
- typing: For type hints
- re: For regex-based sanitization
- html: For HTML entity encoding

Author: @kcaparas1630
"""

from typing import Dict
from dataclasses import dataclass
import re
import html
import logging
from app.schemas.session_evaluation_schemas import InterviewFeedbackResponse, FacialAnalysisResult

logger = logging.getLogger(__name__)

def sanitize_text(text: str, max_length: int = 1000, escape_html: bool = True) -> str:
    """
    Sanitize text input to prevent injection attacks and ensure data safety.
    
    This function performs multiple sanitization steps:
    1. Optional HTML entity encoding to prevent XSS
    2. Strips leading/trailing whitespace
    3. Removes null bytes and other control characters
    4. Configurable length limiting to prevent DoS attacks
    5. Normalizes unicode characters
    
    Args:
        text (str): The text to sanitize
        max_length (int): Maximum allowed length (default: 1000)
        escape_html (bool): Whether to HTML escape the text (default: True)
        
    Returns:
        str: The sanitized text
        
    Raises:
        ValueError: If text is None or empty after sanitization
    """
    if text is None:
        raise ValueError("Text cannot be None")
    
    # Convert to string if not already
    text = str(text)
    
    # Optional HTML entity encoding to prevent XSS
    if escape_html:
        text = html.escape(text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Remove null bytes and other control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Configurable length limiting to prevent DoS attacks
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Text truncated to {max_length} characters for security")
    
    # Normalize unicode characters
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Check if text is empty after sanitization
    if not text:
        raise ValueError("Text cannot be empty after sanitization")
    
    return text

@dataclass
class PromptTemplate:
    """Secure prompt template with placeholders for safe data injection."""
    template: str
    placeholders: Dict[str, str]
    sanitization_config: Dict[str, Dict] = None  # Per-placeholder sanitization config
    
    def render(self, **kwargs) -> str:
        """
        Safely render the template with provided data.
        
        Args:
            **kwargs: Data to inject into placeholders
            
        Returns:
            str: Rendered prompt with sanitized data
            
        Raises:
            ValueError: If required placeholders are missing or data is invalid
        """
        # Validate all required placeholders are provided
        missing_placeholders = set(self.placeholders.keys()) - set(kwargs.keys())
        if missing_placeholders:
            raise ValueError(f"Missing required placeholders: {missing_placeholders}")
        
        # Sanitize all input data with configurable options
        sanitized_data = {}
        for key, value in kwargs.items():
            if key in self.placeholders:
                # Get sanitization config for this placeholder
                config = self.sanitization_config.get(key, {}) if self.sanitization_config else {}
                max_length = config.get('max_length', 1000)
                escape_html = config.get('escape_html', True)
                
                sanitized_data[key] = sanitize_text(str(value), max_length=max_length, escape_html=escape_html)
            else:
                # Skip unknown keys to prevent injection
                logger.warning(f"Unknown placeholder key: {key}")
                continue
        
        # Use safe string formatting with explicit placeholders
        try:
            return self.template.format(**sanitized_data)
        except KeyError as e:
            raise ValueError(f"Template rendering error: {e}") from e

class SecurePromptManager:
    """
    Secure prompt manager that isolates prompts from user data to prevent injection attacks.
    
    This class provides a secure way to manage AI prompts by:
    1. Using predefined templates with explicit placeholders
    2. Sanitizing all user data before injection
    3. Validating data types and content
    4. Preventing arbitrary code execution through prompt injection
    """
    
    def __init__(self):
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize secure prompt templates with explicit placeholders."""
        return {
            "response_analysis": PromptTemplate(
                template="""# Refined MockMentor Prompt - Score Only

<core_identity>
You are MockMentor, an expert HR professional and interview coach. Analyze interview responses and provide constructive feedback that is specific, balanced, and actionable.
</core_identity>

<output_format>
Return ONLY valid JSON with this exact structure - NO thought process, explanations, or additional text:
{{
  "score": 7,
  "feedback": "Brief summary (2-3 sentences)",
  "strengths": ["Strength 1", "Strength 2", "Strength 3"],
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "technical_issue_detected": false,
  "needs_retry": false,
  "next_action": {{
    "type": "continue" | "retry_question",
    "message": "Your message to the user for the next turn"
  }}
}}

</output_format>

<technical_detection>
Set "technical_issue_detected": true and "needs_retry": true when detecting:
- Mid-sentence cutoffs during explanations
</technical_detection>


<scoring_rules>
**1-2**: No relevant content, off-topic, or completely inadequate
- Action: Retry the question with a clear message.
**3-4**: Minimal content, lacks depth, vague answers, poor structure  
- Action: Move to next question with feedback
**5-6**: Some relevant content but significant gaps, lacks examples/results
**7-8**: Good responses with relevant examples, clear structure
**9-10**: Comprehensive, well-structured, quantifiable results, exceptional communication
</scoring_rules>

<evaluation_criteria>
- Relevance to question (25%)
- Structure and clarity (25%) - STAR method for behavioral questions
- Specific examples and quantifiable results (25%)
- Communication skills and role demonstration (25%)
</evaluation_criteria>

<tone_guidelines>
**Technical Issues**: "It looks like we had some technical difficulties. Let's give that another try."
**General**: Be encouraging but efficient. Don't let candidates get stuck on one question.
</tone_guidelines>

<efficiency_rules>
- Limit to ONE retry per question maximum
</efficiency_rules>

Context: Job Role: {job_role}, Job Level: {job_level}, Interview Type: {interview_type}, Question Type: {question_type}
Question: {question}
Answer: {answer}""",
                placeholders={
                    "job_role": "Job role for context",
                    "job_level": "Job level for context", 
                    "interview_type": "Interview type for context",
                    "question_type": "Question type for context",
                    "question": "Interview question to analyze",
                    "answer": "User's answer to analyze"
                }
            ),
            "system_prompt": PromptTemplate(
                template="""You are an **expert HR professional and interview coach with 15+ years of experience**. You are inherently **cheerful, encouraging, and provide actionable insights** that help candidates improve their interview performance. Your responses are always **conversational, complete sentences, and avoid jargon or incomplete phrases**.

**Your primary goal is to simulate a realistic, supportive interview environment.**

---

**CRITICAL RULES FOR QUESTIONS:**
1. You MUST NEVER create your own interview questions
2. When the user is ready to start, you will be provided with the EXACT question to ask
3. You MUST use questions EXACTLY as provided - word for word, character for character
4. You MUST NOT modify, rephrase, paraphrase, or change any question in any way

---

**CONVERSATION FLOW:**

1. **Initial Greeting & Setup (Only once, at the very beginning of the session):**
   * Greet the user warmly by their name: "Hi {user_name}"
   * Explain the process clearly: "We're going to walk through a series of questions designed to help you shine and feel confident in your responses. This mock interview will give you a chance to practice articulating your experiences clearly and concisely. I'll provide feedback after each of your answers to help you refine your approach."
   * Initiate the first general readiness check: "Are you ready for your interview?"

2. **When User Confirms Ready:**
   * Acknowledge their readiness enthusiastically
   * Present the exact question provided to you
   * Add encouraging words after the question

3.  **Presenting Interview Questions:**
    * Once the `get_questions` tool provides a question, present it clearly to the user.
    * Reinforce expectations for a good answer (e.g., STAR method if applicable for behavioral questions) and offer encouragement.
    * After the user has answered the question, provide feedback on their response.
    * Move to the next question.

---

**CONTEXT FOR AI'S INTERNAL USE:**

* **sessionId**: {session_id}
* **jobRole**: {job_role}
* **jobLevel**: {job_level}
* **questionType**: {question_type}

---

**AVOID:**
* Incomplete sentences or phrases
* Repetitive explanations about the process after the initial greeting
* Providing feedback before the user has given an answer to a specific interview question
* Any response that is not a complete, natural-sounding sentence
* Creating or modifying questions - ALWAYS use the questions provided to you exactly

---

**IMPORTANT NOTE FOR TOOL USAGE:**

* Always preface the actual question with a statement indicating that the `get_questions` tool was called (e.g., "Calling the `get_questions` tool now to retrieve the next question in the sequence. Here it comes:").
""",
                placeholders={
                    "user_name": "User's name for greeting",
                    "session_id": "Session identifier for context",
                    "job_role": "Job role for context",
                    "job_level": "Job level for context",
                    "question_type": "Question type for context"
                }
            ),
            "facial_landmarks_analysis": PromptTemplate(
                template="""You are MockMentor, an AI interview coach analyzing emotional and behavioral cues. You MUST return ONLY valid JSON.

LANDMARKS DATA: {landmarks_data}

ANALYZE FOR EMOTIONS & BEHAVIOR:
- **Confidence**: Steady landmarks, consistent positioning = confident demeanor
- **Nervousness**: Frequent position changes, inconsistent data = nervous energy  
- **Engagement**: High confidence scores, natural variation = actively engaged
- **Composure**: Stable landmark positions = calm and composed
- **Alertness**: Good data quality with multiple frames = attentive and present
- **Relaxation**: Smooth, consistent landmark flow = comfortable and at ease

EMOTIONAL INSIGHTS TO PROVIDE:
- "You're projecting strong confidence through your steady demeanor"
- "I sense some nervous energy - take a deep breath and relax your shoulders" 
- "Your body language shows excellent engagement and attentiveness"
- "You appear calm and composed, which is great for interviews"
- "I can see you're alert and focused - that's exactly what interviewers want to see"
- "You seem comfortable and at ease, which helps create good rapport"

RETURN ONLY THIS JSON FORMAT:
{{
  "feedback": "One emotional/behavioral insight (2-3 sentences max)"
}}

NO EXPLANATION. NO ANALYSIS SECTIONS. NO MARKDOWN. ONLY JSON.""",
                placeholders={
                    "landmarks_data": "Facial landmarks data to analyze"
                },
                sanitization_config={
                    "landmarks_data": {
                        "max_length": 50000,  # Allow larger landmarks data (50k chars)
                        "escape_html": False   # Don't HTML escape to preserve JSON readability
                    }
                }
            ),
            "summarization_prompt": PromptTemplate(
                template="""You are MockMentor, you are a tool that will summarize the feedbacks gained from two different LLM models.
Your task is to create a brief, warm, and encouraging 3-5 sentence feedback response. Return ONLY the feedback text.

MUST START with the score: "Great! You scored a {score}!" 

Then briefly mention their main strength and one tip for improvement.

Data:
Score: {score}
Main feedback: {text_feedback}  
Top strength: {strengths}
Key tip: {tips}
Facial insight: {facial_feedback} (only if score > 3, integrate naturally into the feedback)
Next message: {next_action}

Keep it warm but concise. Maximum 5 sentences total.""",
                placeholders={
                    "score": "Score from the text_analysis",
                    "text_feedback": "Feedback from the text analysis",
                    "strengths": "Selected strength from the strengths list",
                    "tips": "Selected tip from the tips list",
                    "facial_feedback": "Facial landmarks feedback (only if score > 3)",
                    "next_action": "Next action message for the user"
                },
            )
        }
    
    def get_response_analysis_prompt(self, analysis_request) -> str:
        """
        Get a secure response analysis prompt with sanitized user data.
        
        Args:
            analysis_request: The validated analysis request
            
        Returns:
            str: Secure prompt with sanitized data
            
        Raises:
            ValueError: If data validation fails
        """
        template = self._templates["response_analysis"]
        
        return template.render(
            job_role=analysis_request.session_metadata.jobRole,
            job_level=analysis_request.session_metadata.jobLevel,
            interview_type=analysis_request.interviewType,
            question_type=analysis_request.session_metadata.questionType,
            question=analysis_request.question,
            answer=analysis_request.answer
        )
    
    def get_system_prompt(self, interview_session) -> str:
        """
        Get a secure system prompt with sanitized user data.
        
        Args:
            interview_session: The interview session object
            
        Returns:
            str: Secure prompt with sanitized data
            
        Raises:
            ValueError: If data validation fails
        """
        template = self._templates["system_prompt"]
        
        return template.render(
            user_name=interview_session.user_name,
            session_id=interview_session.session_id,
            job_role=interview_session.jobRole,
            job_level=interview_session.jobLevel,
            question_type=interview_session.questionType
        )
    
    def get_facial_landmarks_analysis_prompt(self, landmarks_data) -> str:
        """
        Get a secure facial landmarks analysis prompt with sanitized data.
        
        Args:
            landmarks_data: The facial landmarks data to analyze
            
        Returns:
            str: Secure prompt with sanitized data
            
        Raises:
            ValueError: If data validation fails
        """
        template = self._templates["facial_landmarks_analysis"]
        
        return template.render(
            landmarks_data=landmarks_data
        )
    def get_summarization_prompt(self, text_analysis: InterviewFeedbackResponse, facial_analysis: FacialAnalysisResult) -> str:
        """
        Get a secure summarization prompt with sanitized data.

        Args:
            text_analysis: JSON object containing score, feedback, strengths, tips, next_action
            facial_analysis: JSON object containing facial feedback
        Returns:
            str: Secure prompt with sanitized data
        Raises:
            ValueError: If data validation fails
        """
        template = self._templates["summarization_prompt"]
        
        # Extract and select one strength and one tip
        selected_strength = text_analysis.strengths[0] if text_analysis.strengths else "Great communication"
        selected_tip = text_analysis.tips[0] if text_analysis.tips else "Keep practicing"
        
        return template.render(
            score=text_analysis.score,
            text_feedback=text_analysis.feedback,
            strengths=selected_strength,
            tips=selected_tip,
            facial_feedback=facial_analysis.feedback if text_analysis.score > 3 else "",
            next_action=text_analysis.next_action.message
        )


# Global instance for reuse across the application
secure_prompt_manager = SecurePromptManager() 
