from typing import Dict, List
from .get_conversation_context import get_conversation_context

def _add_to_context(session_id: str, role: str, content: str, _conversation_contexts: Dict[str, List[Dict]]) -> None:
        """
        Add a message to the conversation context.
        
        Args:
            session_id (str): The session identifier.
            role (str): The role of the message sender (e.g., 'user', 'assistant', 'system').
            content (str): The message content.
        """
        context = get_conversation_context(session_id, _conversation_contexts)
        context.append({"role": role, "content": content})
