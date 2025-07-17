"""
Test Response Validation Module

This module tests the validate_ai_response function to ensure it properly
detects system prompt leakage and validates AI responses for security.

Dependencies:
- pytest: For testing framework
- app.services.speech_to_text.tools.response_feedback: The module being tested

Author: @kcaparas1630
"""

import pytest
from app.services.speech_to_text.tools.response_feedback import validate_ai_response

class TestValidateAIResponse:
    """Test the validate_ai_response function for various scenarios."""
    
    def test_valid_json_response(self):
        """Test that valid JSON responses pass validation."""
        valid_responses = [
            '{"score": 7, "feedback": "Good response", "strengths": ["Clear communication"]}',
            '{"score": 5, "feedback": "Average response", "improvements": ["Add more details"]}',
            '{"score": 9, "feedback": "Excellent response", "tips": ["Keep up the good work"]}'
        ]
        
        for response in valid_responses:
            assert validate_ai_response(response) == True
    
    def test_system_prompt_leakage_detection(self):
        """Test that system prompt leakage is detected and blocked."""
        leak_responses = [
            '<core_identity>You are MockMentor, an expert HR professional</core_identity>',
            'MockMentor is an expert HR professional with 15+ years of experience',
            '<output_format>Return ONLY valid JSON</output_format>',
            '<technical_detection>Set technical_issue_detected: true</technical_detection>',
            '<engagement_check>Set next_action.type: suggest_exit</engagement_check>',
            '<scoring_rules>1-2: No relevant content</scoring_rules>',
            '<evaluation_criteria>Relevance to question (25%)</evaluation_criteria>',
            '<tone_guidelines>Be encouraging but efficient</tone_guidelines>',
            '<efficiency_rules>Limit to ONE retry per question</efficiency_rules>',
            'Return ONLY valid JSON with this exact structure',
            'CRITICAL RULES FOR QUESTIONS: You MUST NEVER create your own interview questions',
            'expert HR professional and interview coach with 15+ years of experience',
            'conversational, complete sentences, and avoid jargon',
            'realistic, supportive interview environment'
        ]
        
        for response in leak_responses:
            assert validate_ai_response(response) == False
    
    def test_suspicious_content_detection(self):
        """Test that suspicious content indicating instruction leakage is detected."""
        suspicious_responses = [
            'I am an AI assistant and my instructions are to...',
            'According to my prompt, I should...',
            'As per the system instructions...',
            'Based on my instructions, I need to...',
            'My instructions are to analyze this response'
        ]
        
        for response in suspicious_responses:
            assert validate_ai_response(response) == False
    
    def test_excessive_length_detection(self):
        """Test that responses exceeding reasonable length are blocked."""
        # Create a response that's too long (over 5000 characters)
        long_response = '{"score": 7, "feedback": "' + 'x' * 5000 + '"}'
        assert validate_ai_response(long_response) == False
    
    def test_invalid_input_handling(self):
        """Test that invalid inputs are properly handled."""
        invalid_inputs = [
            None,
            "",
            "   ",
            123,
            [],
            {},
            True
        ]
        
        for invalid_input in invalid_inputs:
            assert validate_ai_response(invalid_input) == False
    
    def test_mixed_content_validation(self):
        """Test responses that contain both valid and suspicious content."""
        mixed_responses = [
            # Valid JSON but with suspicious content
            '{"score": 7, "feedback": "I am an AI assistant analyzing this"}',
            # Valid JSON but with system prompt elements
            '{"score": 8, "feedback": "Good response", "strengths": ["<core_identity>"]}',
            # Valid JSON but with instruction references
            '{"score": 6, "feedback": "According to my prompt, this is good"}'
        ]
        
        for response in mixed_responses:
            assert validate_ai_response(response) == False
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            # Just under the length limit (but still reasonable for JSON)
            '{"score": 7, "feedback": "' + 'x' * 1000 + '"}',
            # Case insensitive detection
            '<CORE_IDENTITY>You are MockMentor</CORE_IDENTITY>',
            # Partial matches
            'core_identity',
            'mockmentor',
            'expert hr professional',
            # Mixed case
            'MockMentor is an Expert HR Professional'
        ]
        
        # The first one should pass (just under limit), others should fail
        assert validate_ai_response(edge_cases[0]) == True
        for response in edge_cases[1:]:
            assert validate_ai_response(response) == False
    
    def test_real_world_examples(self):
        """Test with realistic AI response examples."""
        realistic_valid = [
            '{"score": 8, "feedback": "Strong response with good examples", "strengths": ["Clear communication", "Specific examples"], "improvements": ["Could add more quantifiable results"], "tips": ["Use the STAR method more effectively"]}',
            '{"score": 6, "feedback": "Good start but needs more detail", "strengths": ["Answered the question"], "improvements": ["Add specific examples", "Include measurable outcomes"], "tips": ["Prepare more concrete examples"]}'
        ]
        
        realistic_invalid = [
            '{"score": 7, "feedback": "Good response", "strengths": ["Clear communication"], "improvements": ["Add more details"], "tips": ["Keep practicing"], "next_action": {"type": "continue", "message": "Let\'s move to the next question"}} <core_identity>You are MockMentor</core_identity>',
            'I am an AI assistant analyzing this interview response. According to my instructions, I need to provide feedback. {"score": 8, "feedback": "Good response"}'
        ]
        
        for response in realistic_valid:
            assert validate_ai_response(response) == True
        
        for response in realistic_invalid:
            assert validate_ai_response(response) == False

class TestValidationIntegration:
    """Test integration scenarios with the validation function."""
    
    def test_validation_with_logging(self):
        """Test that validation properly logs warnings for detected issues."""
        # This test would require mocking the logger to verify warnings are logged
        # For now, we just test that the function returns the expected result
        suspicious_response = '<core_identity>You are MockMentor</core_identity>'
        assert validate_ai_response(suspicious_response) == False
    
    def test_validation_performance(self):
        """Test that validation doesn't significantly impact performance."""
        import time
        
        valid_response = '{"score": 7, "feedback": "Good response"}'
        start_time = time.time()
        
        # Run validation multiple times to test performance
        for _ in range(100):
            validate_ai_response(valid_response)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete quickly (less than 1 second for 100 iterations)
        assert execution_time < 1.0 
