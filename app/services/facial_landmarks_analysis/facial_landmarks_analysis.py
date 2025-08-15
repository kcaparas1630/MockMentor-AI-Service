"""
Facial Emotion Analysis Service Module

This module provides AI-powered analysis of compressed facial emotion features to generate
real-time feedback on interview behavior. It processes pre-computed emotional metrics
from client-side MediaPipe analysis to provide contextual behavioral feedback.

Updated to work with compressed emotion features instead of raw landmarks for
better performance and reduced data transfer.

Dependencies:
- openai: For AI client interactions and response generation
- app.core.secure_prompt_manager: For secure prompt management
- logging: For error logging and debugging
- json: For response parsing

Author: @kcaparas1630
"""

from openai import AsyncOpenAI
from app.core.secure_prompt_manager import secure_prompt_manager
from app.core.ai_client_manager import get_facial_analysis_client
from app.schemas.session_evaluation_schemas import FacialAnalysisResult
import logging
import json
import time
import re
import traceback
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EmotionFeatures(BaseModel):
    """
    Compressed emotion features from client-side MediaPipe analysis.
    All values are on 0-100 scale for easier processing.
    """
    smile: int  # 0-100: smile intensity
    eyeOpen: int  # 0-100: eye openness
    browRaise: int  # 0-100: eyebrow raise
    mouthOpen: int  # 0-100: mouth openness
    tension: int  # 0-100: facial tension
    symmetry: int  # 0-100: facial symmetry
    confidence: int  # 0-100: MediaPipe detection confidence
    timestamp: int  # Timestamp from client
    frameId: str  # Unique frame identifier

class FacialEmotionAnalysis:
    """
    Service class for analyzing compressed emotion features and providing
    real-time behavioral feedback during interviews using LLM processing.
    """
    
    def __init__(self):
        """Initialize the facial emotion analysis service."""
        self.last_analysis_time = 0
        self.analysis_history = []  # Store recent analyses for context
        self.max_history = 5  # Keep last 5 analyses for trend detection
    
    def _prepare_emotion_context(self, features: EmotionFeatures) -> str:
        """
        Prepare rich context from emotion features for LLM analysis.
        
        Args:
            features (EmotionFeatures): The compressed emotion features
            
        Returns:
            str: Formatted context string for LLM prompt
        """
        # Convert to descriptive ranges for better LLM understanding
        def get_level(value: int) -> str:
            if value >= 80: return "very high"
            elif value >= 60: return "high"
            elif value >= 40: return "moderate"
            elif value >= 20: return "low"
            else: return "very low"
        
        def get_confidence_level(value: int) -> str:
            if value >= 90: return "excellent"
            elif value >= 75: return "good"
            elif value >= 50: return "moderate"
            else: return "low"
        
        # Interpret facial metrics
        context = f"""
FACIAL EMOTION ANALYSIS DATA:

Core Emotions:
- Smile Intensity: {features.smile}/100 ({get_level(features.smile)})
- Eye Openness: {features.eyeOpen}/100 ({get_level(features.eyeOpen)})
- Eyebrow Raise: {features.browRaise}/100 ({get_level(features.browRaise)})
- Mouth Openness: {features.mouthOpen}/100 ({get_level(features.mouthOpen)})

Facial Control:
- Facial Tension: {features.tension}/100 ({get_level(features.tension)})
- Facial Symmetry: {features.symmetry}/100 ({get_level(features.symmetry)})
- Detection Quality: {features.confidence}/100 ({get_confidence_level(features.confidence)})

INTERPRETATION GUIDE:
- High smile + moderate eye openness = confident/happy
- High tension + low symmetry = nervous/anxious
- High eyebrow + wide eyes = surprised/alert
- Balanced metrics + good symmetry = composed/professional
- High eye openness + low tension = focused/engaged
- Low smile + moderate features = neutral/serious

CONTEXT NOTES:
- Timestamp: {features.timestamp}
- Frame ID: {features.frameId}
- Analysis quality is {get_confidence_level(features.confidence)} based on detection confidence
"""
        
        # Add trend analysis if we have history
        if len(self.analysis_history) > 1:
            context += self._get_trend_analysis()
        
        return context
    
    def _get_trend_analysis(self) -> str:
        """
        Analyze trends from recent emotion data.
        
        Returns:
            str: Trend analysis context
        """
        if len(self.analysis_history) < 2:
            return ""
        
        current = self.analysis_history[-1]
        previous = self.analysis_history[-2]
        
        trends = []
        
        # Check for significant changes (>15 points)
        smile_change = current.get('smile', 0) - previous.get('smile', 0)
        tension_change = current.get('tension', 0) - previous.get('tension', 0)
        eye_change = current.get('eyeOpen', 0) - previous.get('eyeOpen', 0)
        
        if abs(smile_change) > 15:
            direction = "increased" if smile_change > 0 else "decreased"
            trends.append(f"Smile intensity has {direction} significantly")
        
        if abs(tension_change) > 15:
            direction = "increased" if tension_change > 0 else "decreased"
            trends.append(f"Facial tension has {direction}")
        
        if abs(eye_change) > 15:
            direction = "improved" if eye_change > 0 else "reduced"
            trends.append(f"Eye engagement has {direction}")
        
        if trends:
            return f"\nRECENT TRENDS:\n- " + "\n- ".join(trends) + "\n"
        
        return "\nRECENT TRENDS: Expression remains stable\n"
    
    def _store_analysis_history(self, features: EmotionFeatures):
        """Store features in history for trend analysis."""
        feature_dict = {
            'smile': features.smile,
            'eyeOpen': features.eyeOpen,
            'browRaise': features.browRaise,
            'mouthOpen': features.mouthOpen,
            'tension': features.tension,
            'symmetry': features.symmetry,
            'confidence': features.confidence,
            'timestamp': features.timestamp
        }
        
        self.analysis_history.append(feature_dict)
        
        # Keep only recent history
        if len(self.analysis_history) > self.max_history:
            self.analysis_history.pop(0)
    
    async def analyze_emotion_features(
        self, 
        features_data: Dict[str, Any], 
        client: AsyncOpenAI = None
    ) -> FacialAnalysisResult:
        """
        Analyze compressed emotion features and provide behavioral feedback using LLM.
        
        Args:
            features_data (Dict): The emotion features data from client
            client (AsyncOpenAI): The OpenAI client instance
            
        Returns:
            FacialAnalysisResult: Analysis result containing feedback
            
        Raises:
            Exception: If there's a critical error in the analysis process
        """
        try:
            logger.info("[ENTRY] analyze_emotion_features function called - ENTRY POINT")
            
            total_start_time = time.time()
            
            # Validate and parse emotion features
            try:
                features = EmotionFeatures(**features_data)
                logger.debug(f"Successfully parsed emotion features: {features}")
            except Exception as e:
                logger.error(f"Failed to parse emotion features: {e}")
                return FacialAnalysisResult(
                    feedback="Invalid emotion data received. Please ensure your camera is working properly."
                )
            
            # Store for trend analysis
            self._store_analysis_history(features)
            
            # Use dedicated client if not provided
            if client is None:
                client = get_facial_analysis_client()
                logger.debug("Using dedicated facial analysis client")
            else:
                logger.debug("Using provided client for facial analysis")
            
            # Prepare rich context for LLM
            emotion_context = self._prepare_emotion_context(features)
            
            # Use secure prompt manager with emotion context
            system_prompt = secure_prompt_manager.get_emotion_analysis_prompt(emotion_context)
            
            llm_start_time = time.time()
            
            response = await client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-8B-Instruct-fast",
                max_tokens=300,  # Reduced since we need concise feedback
                temperature=0.3,  # Slightly higher for more varied responses
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
                                "text": f"Analyze this emotion data and provide specific, actionable feedback:\n\n{emotion_context}"
                            }
                        ]
                    }
                ]
            )
            
            llm_duration = time.time() - llm_start_time
            logger.info(f"LLM call completed in {llm_duration:.3f}s")
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                feedback_data = json.loads(content.strip())
                logger.info(f"[EMOTION_ANALYSIS] Successfully parsed JSON: {feedback_data}")
                
                total_duration = time.time() - total_start_time
                logger.info(f"[PERF] Total analyze_emotion_features completed in {total_duration:.3f}s")
                
                return FacialAnalysisResult(
                    feedback=feedback_data.get("feedback", "Analysis complete")
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Content that failed to parse: {content}")
                
                # Try to extract JSON from the response if it's mixed with other text
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    try:
                        fallback_data = json.loads(json_match.group())
                        logger.info(f"Successfully extracted JSON from mixed response: {fallback_data}")
                        return FacialAnalysisResult(
                            feedback=fallback_data.get("feedback", "Analysis complete")
                        )
                    except json.JSONDecodeError:
                        pass
                
                # Extract plain text feedback if JSON parsing fails completely
                clean_content = re.sub(r'[{}"]', '', content).strip()
                if clean_content:
                    return FacialAnalysisResult(
                        feedback=clean_content[:200] + ("..." if len(clean_content) > 200 else "")
                    )
                
                # Return structured fallback response
                return FacialAnalysisResult(
                    feedback="I can see your facial expression but need better data quality for detailed analysis. Please ensure good lighting and face the camera directly."
                )
                
        except Exception as e:
            logger.error(f"[ERROR] Exception in analyze_emotion_features: {type(e).__name__}: {e}")
            logger.error(f"[ERROR] Full traceback: {traceback.format_exc()}")
            
            # Return error response
            return FacialAnalysisResult(
                feedback="Technical error occurred during emotion analysis. Please try again."
            )
    
    # Backward compatibility method
    async def analyze_landmarks(self, client: AsyncOpenAI = None, landmarks_data: str = "") -> FacialAnalysisResult:
        """
        Backward compatibility method for existing code.
        Now expects JSON string with emotion features instead of raw landmarks.
        """
        try:
            # Try to parse as emotion features JSON
            features_data = json.loads(landmarks_data)
            return await self.analyze_emotion_features(features_data, client)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON landmarks data, returning fallback response")
            return FacialAnalysisResult(
                feedback="Please use the updated emotion analysis format for better feedback."
            )

# Global instance for reuse across the application
facial_emotion_analyzer = FacialEmotionAnalysis()

# Keep backward compatibility
facial_landmarks_analyzer = facial_emotion_analyzer