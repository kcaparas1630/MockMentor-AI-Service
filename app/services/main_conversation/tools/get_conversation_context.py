from typing import Dict, List
def _get_conversation_context(session_id: str, _conversation_contexts: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Get or initialize conversation context for a session.
        
        Args:
            session_id (str): The unique identifier for the interview session.
            
        Returns:
            List[Dict]: The conversation context for the specified session.
        """
        if session_id not in _conversation_contexts:
            _conversation_contexts[session_id] = []
        return _conversation_contexts[session_id]
