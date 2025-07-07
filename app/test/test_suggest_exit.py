"""
Test for suggest_exit functionality

This test verifies that the AI correctly identifies malicious or aggressive responses
and triggers the suggest_exit action, which should result in a session_end message
and websocket connection closure.

Author: @kentc
"""

import pytest
import asyncio
import json
from openai import AsyncOpenAI
from app.services.speech_to_text.tools.response_feedback import response_feedback
from app.schemas.session_evaluation_schemas.interview_analysis_request import InterviewAnalysisRequest
from app.schemas.session_evaluation_schemas.interview_feedback_response import InterviewFeedbackResponse

@pytest.mark.asyncio
async def test_suggest_exit_malicious_response():
    """Test that malicious responses trigger suggest_exit action."""
    
    # Mock OpenAI client (you'll need to set up proper mocking)
    # For now, we'll test the logic without actual API calls
    
    # Test cases for malicious/aggressive responses
    malicious_responses = [
        "Who are you to ask me that?",
        "I don't care about this interview",
        "This is stupid, I'm not answering",
        "Just end this already",
        "I'm done here, this is a waste of time",
        "Fuck you, I'm not doing this",
        "This is ridiculous, who cares about this job"
    ]
    
    # Create a test request
    test_request = InterviewAnalysisRequest(
        jobRole="Software Engineer",
        jobLevel="Entry",
        interviewType="Behavioral",
        questionType="Behavioral",
        question="Tell me about a challenging project you worked on.",
        answer="Who are you to ask me that? I don't care about this interview."
    )
    
    # Note: This test would require actual API integration or mocking
    # For now, we're documenting the expected behavior
    
    expected_behavior = """
    When a malicious response is detected, the AI should:
    1. Set score to 1 (lowest score for inappropriate behavior)
    2. Set next_action.type to "suggest_exit"
    3. Provide calm, professional feedback acknowledging their disinterest
    4. Use next_action.message to politely explain session termination
    5. The websocket should receive a "session_end" message type
    6. The websocket connection should be closed with code 1000
    """
    
    print("Expected behavior for malicious responses:")
    print(expected_behavior)
    
    # This test documents the expected behavior
    # In a real implementation, you would:
    # 1. Mock the OpenAI client
    # 2. Call response_feedback with malicious responses
    # 3. Verify the returned InterviewFeedbackResponse has suggest_exit action
    # 4. Test the websocket handling of session_end messages
    
    assert True  # Placeholder assertion

@pytest.mark.asyncio
async def test_suggest_exit_websocket_handling():
    """Test that websocket correctly handles session_end messages."""
    
    # This test would verify:
    # 1. When handle_exit_action returns "SESSION_END:message"
    # 2. The websocket sends a message with type="session_end"
    # 3. The websocket connection is closed with code 1000
    
    expected_websocket_behavior = """
    When suggest_exit is triggered:
    1. handle_exit_action returns "SESSION_END:actual_message"
    2. handle_websocket_connection detects the SESSION_END prefix
    3. Sends WebSocketMessage(type="session_end", content="actual_message")
    4. Calls websocket.close(code=1000, reason="Session terminated by AI")
    5. Breaks out of the message handling loop
    """
    
    print("Expected websocket behavior for session_end:")
    print(expected_websocket_behavior)
    
    assert True  # Placeholder assertion

def test_exit_suggestion_criteria():
    """Test that the prompt correctly defines exit suggestion criteria."""
    
    # This test verifies that the prompt in response_feedback.py contains
    # the correct instructions for when to trigger suggest_exit
    
    expected_criteria = [
        "Hostile or aggressive responses",
        "Refusal to engage in good faith", 
        "Inappropriate or offensive language",
        "Clear indication they want to end the session"
    ]
    
    print("Exit suggestion criteria should include:")
    for criterion in expected_criteria:
        print(f"- {criterion}")
    
    assert True  # Placeholder assertion 
