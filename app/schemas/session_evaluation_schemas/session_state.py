"""
Session State Schemas

This module defines typed schemas for managing interview session state,
including pending analyses coordination and session metadata.

These schemas provide type safety for session state management and
ensure proper coordination between text analysis and facial analysis
before generating unified feedback.

Dependencies:
- pydantic: For data validation and serialization
- typing: For type hints

Author: @kcaparas1630
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class AnalysisStatus(str, Enum):
    """Status of analysis completion."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionMetadata(BaseModel):
    """Session metadata containing user and interview details."""
    user_name: str = Field(..., description="Name of the interview candidate")
    jobRole: str = Field(..., description="Target job role for the interview")
    jobLevel: str = Field(..., description="Job level (e.g., entry, mid, senior)")
    questionType: str = Field(..., description="Type of interview questions")


class NextAction(BaseModel):
    """Next action information from text analysis."""
    type: str = Field(..., description="Action type (continue, retry_question, etc.)")
    message: str = Field(..., description="Message to display to the user")


class TextAnalysisResult(BaseModel):
    """Results from text analysis of user's answer."""
    score: int = Field(..., ge=0, le=10, description="Interview response score (0-10)")
    feedback: str = Field(..., description="Brief summary feedback (2-3 sentences)")
    strengths: List[str] = Field(default_factory=list, description="User's identified strengths")
    tips: List[str] = Field(default_factory=list, description="Tips for improvement")
    technical_issue_detected: bool = Field(default=False, description="Whether technical issues were detected")
    needs_retry: bool = Field(default=False, description="Whether the question needs to be retried")
    next_action: NextAction = Field(..., description="Next action information")


class FacialAnalysisResult(BaseModel):
    """Results from facial landmarks analysis."""
    feedback: str = Field(..., description="Emotional/behavioral insight (2-3 sentences max)")


class PendingAnalyses(BaseModel):
    """Container for tracking pending analysis results."""
    text_analysis: Optional[TextAnalysisResult] = Field(default=None, description="Text analysis result")
    facial_analysis: Optional[FacialAnalysisResult] = Field(default=None, description="Facial analysis result")
    text_status: AnalysisStatus = Field(default=AnalysisStatus.PENDING, description="Text analysis status")
    facial_status: AnalysisStatus = Field(default=AnalysisStatus.PENDING, description="Facial analysis status")
    waiting_for_feedback: bool = Field(default=True, description="Whether session is waiting for unified feedback")
    
    def is_complete(self) -> bool:
        """Check if both analyses are completed successfully."""
        return (
            self.text_status == AnalysisStatus.COMPLETED and 
            self.facial_status == AnalysisStatus.COMPLETED and
            self.text_analysis is not None and 
            self.facial_analysis is not None
        )
    
    def has_text_analysis(self) -> bool:
        """Check if text analysis is completed."""
        return self.text_status == AnalysisStatus.COMPLETED and self.text_analysis is not None
    
    def has_facial_analysis(self) -> bool:
        """Check if facial analysis is completed."""
        return self.facial_status == AnalysisStatus.COMPLETED and self.facial_analysis is not None


class SessionState(BaseModel):
    """Complete session state with type safety."""
    ready: bool = Field(default=False, description="Whether user is ready to start interview")
    current_question_index: int = Field(default=0, description="Index of current question")
    waiting_for_answer: bool = Field(default=False, description="Whether session is waiting for user answer")
    retry_attempts: int = Field(default=0, description="Number of retry attempts for current question")
    session_metadata: SessionMetadata = Field(..., description="Interview session metadata")
    pending_analyses: Optional[PendingAnalyses] = Field(default=None, description="Pending analysis results coordination")
    
    def start_analyses(self) -> None:
        """Initialize pending analyses for coordination."""
        self.pending_analyses = PendingAnalyses()
    
    def set_text_analysis(self, result: TextAnalysisResult) -> None:
        """Set text analysis result."""
        if self.pending_analyses is None:
            self.start_analyses()
        self.pending_analyses.text_analysis = result
        self.pending_analyses.text_status = AnalysisStatus.COMPLETED
    
    def set_facial_analysis(self, result: FacialAnalysisResult) -> None:
        """Set facial analysis result."""
        if self.pending_analyses is None:
            self.start_analyses()
        self.pending_analyses.facial_analysis = result
        self.pending_analyses.facial_status = AnalysisStatus.COMPLETED
    
    def mark_text_analysis_failed(self) -> None:
        """Mark text analysis as failed."""
        if self.pending_analyses is None:
            self.start_analyses()
        self.pending_analyses.text_status = AnalysisStatus.FAILED
    
    def mark_facial_analysis_failed(self) -> None:
        """Mark facial analysis as failed."""
        if self.pending_analyses is None:
            self.start_analyses()
        self.pending_analyses.facial_status = AnalysisStatus.FAILED
    
    def is_ready_for_unified_feedback(self) -> bool:
        """Check if both analyses are complete and ready for unified feedback."""
        return (
            self.pending_analyses is not None and 
            self.pending_analyses.is_complete() and 
            self.pending_analyses.waiting_for_feedback
        )
    
    def clear_analyses(self) -> None:
        """Clear pending analyses after feedback generation."""
        self.pending_analyses = None


class SessionStateDict(BaseModel):
    """Type-safe container for session states dictionary."""
    sessions: Dict[str, SessionState] = Field(default_factory=dict, description="Session states by session ID")
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state by ID."""
        return self.sessions.get(session_id)
    
    def create_session(self, session_id: str, metadata: SessionMetadata) -> SessionState:
        """Create new session state."""
        session_state = SessionState(session_metadata=metadata)
        self.sessions[session_id] = session_state
        return session_state
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self.sessions