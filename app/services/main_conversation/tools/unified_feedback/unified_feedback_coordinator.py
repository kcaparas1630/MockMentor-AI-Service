"""
Unified Feedback Coordinator Utility Module

This module provides functionality to coordinate unified feedback generation
when both text analysis and facial analysis are complete. It implements the
DRY principle by centralizing the logic for checking readiness and generating
unified feedback.

Dependencies:
- app.schemas.session_evaluation_schemas.session_state: For SessionState management
- app.services.evaluation_summary.evaluation_summary_service: For unified feedback generation
- loguru: For logging operations

Author: @kcaparas1630
"""

import asyncio
from typing import Optional
from loguru import logger
from app.schemas.session_evaluation_schemas import SessionState
from app.services.evaluation_summary.evaluation_summary_service import evaluation_summary_service


async def check_and_generate_unified_feedback(session_state: SessionState, session_id: str) -> Optional[str]:
    """
    Check if unified feedback is ready and generate it if both analyses are complete.
    
    This function implements the core logic for coordinating unified feedback generation.
    It should be called after storing either text analysis or facial analysis results.
    
    Args:
        session_state: The current session state containing analysis results
        session_id: The session identifier for logging purposes
        
    Returns:
        Optional[str]: The unified feedback text if generated, None if not ready or failed
        
    Flow:
        1. Check if both analyses are complete using session_state.is_ready_for_unified_feedback()
        2. If ready, generate unified feedback using evaluation_summary_service
        3. Clear analyses from session state after successful generation
        4. Return the unified feedback text for sending to client
    """
    if not session_state.is_ready_for_unified_feedback():
        # Provide precise debug logging about which analysis is missing
        if session_state.pending_analyses is None:
            logger.debug(f"[UNIFIED_FEEDBACK] Not ready for session {session_id} - no analyses started")
        else:
            text_ready = session_state.pending_analyses.has_text_analysis()
            facial_ready = session_state.pending_analyses.has_facial_analysis()
            
            if not text_ready and not facial_ready:
                logger.debug(f"[UNIFIED_FEEDBACK] Not ready for session {session_id} - waiting for both text and facial analysis")
            elif not text_ready:
                logger.debug(f"[UNIFIED_FEEDBACK] Not ready for session {session_id} - waiting for text analysis (facial analysis complete)")
            elif not facial_ready:
                logger.debug(f"[UNIFIED_FEEDBACK] Not ready for session {session_id} - waiting for facial analysis (text analysis complete)")
            else:
                logger.debug(f"[UNIFIED_FEEDBACK] Not ready for session {session_id} - analyses complete but not waiting for feedback")
        
        return None
    
    logger.info(f"[UNIFIED_FEEDBACK] Both analyses complete for session {session_id}, generating unified feedback")
    
    try:
        # Get the stored analysis results
        text_analysis = session_state.pending_analyses.text_analysis
        facial_analysis = session_state.pending_analyses.facial_analysis
        
        if not text_analysis or not facial_analysis:
            logger.error(f"[UNIFIED_FEEDBACK] Missing analysis data for session {session_id}")
            return None
        
        # Generate unified feedback using the evaluation summary service
        unified_feedback = await evaluation_summary_service.create_summary_with_fallback(
            text_analysis=text_analysis,
            facial_analysis=facial_analysis
        )
        
        if unified_feedback:
            logger.info(f"[UNIFIED_FEEDBACK] Successfully generated unified feedback for session {session_id}")
            logger.debug(f"[UNIFIED_FEEDBACK] Preview: {unified_feedback[:100]}...")
            
            # Clear analyses after successful generation
            session_state.clear_analyses()
            
            return unified_feedback
        else:
            logger.warning(f"[UNIFIED_FEEDBACK] Generated empty feedback for session {session_id}")
            return None
            
    except Exception as e:
        logger.error(f"[UNIFIED_FEEDBACK] Error generating unified feedback for session {session_id}: {e}")
        return None


async def store_text_analysis_and_check_unified_feedback(
    session_state: SessionState, 
    session_id: str, 
    text_analysis_result
) -> None:
    """
    Store text analysis result in session state.
    
    Note: Unified feedback generation is now handled in action handlers,
    so this function only stores the result without generating feedback.
    
    Args:
        session_state: The current session state
        session_id: The session identifier
        text_analysis_result: The text analysis result to store
    """
    # Store text analysis result
    session_state.set_text_analysis(text_analysis_result)
    logger.info(f"[SESSION_STATE] Stored text analysis result for session {session_id}")
    
    # Log readiness status for debugging
    if session_state.pending_analyses:
        text_ready = session_state.pending_analyses.has_text_analysis()
        facial_ready = session_state.pending_analyses.has_facial_analysis()
        logger.debug(f"[SESSION_STATE] Analysis status for session {session_id}: text={text_ready}, facial={facial_ready}")


async def store_facial_analysis_and_check_unified_feedback(
    session_state: SessionState, 
    session_id: str, 
    facial_analysis_result
) -> None:
    """
    Store facial analysis result in session state.
    
    Note: Unified feedback generation is now handled in action handlers,
    so this function only stores the result without generating feedback.
    
    Args:
        session_state: The current session state
        session_id: The session identifier
        facial_analysis_result: The facial analysis result to store
    """
    # Store facial analysis result
    session_state.set_facial_analysis(facial_analysis_result)
    logger.info(f"[SESSION_STATE] Stored facial analysis result for session {session_id}")
    
    # Log readiness status for debugging
    if session_state.pending_analyses:
        text_ready = session_state.pending_analyses.has_text_analysis()
        facial_ready = session_state.pending_analyses.has_facial_analysis()
        logger.debug(f"[SESSION_STATE] Analysis status for session {session_id}: text={text_ready}, facial={facial_ready}")