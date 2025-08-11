"""
AI Client Manager

This module manages separate AI client instances for different services to prevent
API contention and improve performance. Each service type gets its own dedicated
client instance.
"""

import os
from openai import AsyncOpenAI
import logging
import threading
from typing import Dict, Optional
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

logger = logging.getLogger(__name__)

class AIClientManager:
    """
    Manages dedicated AI client instances for different services.
    
    This singleton class creates and manages separate AsyncOpenAI clients
    for different service types to prevent API contention and improve
    concurrent performance.
    """
    
    _instance: Optional['AIClientManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'AIClientManager':
        """Thread-safe singleton instance getter."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _initialize_clients(self):
        """Lazy initialization of client instances."""
        if self._initialized:
            return
            
        with self._lock:
            # Double-check locking for initialization
            if self._initialized:
                return
                
            api_key = os.getenv("NEBIUS_API_KEY")
            if not api_key:
                # Provide helpful error message for different environments
                if os.getenv("ENV") == "test":
                    logger.warning("NEBIUS_API_KEY not set - using mock clients for testing")
                    # Could implement mock clients here for testing
                    return
                else:
                    raise RuntimeError(
                        "NEBIUS_API_KEY environment variable is not set. "
                        "Please set it in your .env file or environment variables."
                    )
            
            base_url = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1")
            
            # Create dedicated clients for different services
            try:
                self._clients = {
                    "text_analysis": AsyncOpenAI(
                        base_url=base_url,
                        api_key=api_key
                    ),
                    "facial_analysis": AsyncOpenAI(
                        base_url=base_url,
                        api_key=api_key
                    ),
                    "conversation": AsyncOpenAI(
                        base_url=base_url,
                        api_key=api_key
                    ),
                    "transcription": AsyncOpenAI(
                        base_url=base_url,
                        api_key=api_key
                    )
                }
                
                self._initialized = True
                logger.info(f"Initialized {len(self._clients)} dedicated AI client instances")
                
            except Exception as e:
                logger.error(f"Failed to initialize AI clients: {e}")
                raise RuntimeError(f"Failed to initialize AI clients: {e}") from e
    
    def get_client(self, service_type: str) -> AsyncOpenAI:
        """
        Get a dedicated client for the specified service type.
        
        Args:
            service_type (str): Type of service ("text_analysis", "facial_analysis", 
                              "conversation", "transcription")
                              
        Returns:
            AsyncOpenAI: Dedicated client instance for the service
            
        Raises:
            ValueError: If service_type is not supported
            RuntimeError: If clients failed to initialize
        """
        # Lazy initialization on first access
        self._initialize_clients()
        
        if not self._initialized:
            raise RuntimeError("AI clients failed to initialize properly")
            
        if service_type not in self._clients:
            available_types = list(self._clients.keys()) if self._clients else []
            raise ValueError(f"Unsupported service type: {service_type}. Available: {available_types}")
        
        return self._clients[service_type]
    
    def get_text_analysis_client(self) -> AsyncOpenAI:
        """Get dedicated client for text analysis services."""
        return self.get_client("text_analysis")
    
    def get_facial_analysis_client(self) -> AsyncOpenAI:
        """Get dedicated client for facial analysis services."""
        return self.get_client("facial_analysis")
    
    def get_conversation_client(self) -> AsyncOpenAI:
        """Get dedicated client for conversation services."""
        return self.get_client("conversation")
    
    def get_transcription_client(self) -> AsyncOpenAI:
        """Get dedicated client for transcription services."""
        return self.get_client("transcription")

# Lazy initialization - no eager instantiation
_ai_manager: Optional[AIClientManager] = None
_manager_lock = threading.Lock()

def get_ai_client_manager() -> AIClientManager:
    """
    Get the singleton AIClientManager instance with lazy initialization.
    
    This function provides thread-safe access to the AIClientManager singleton,
    initializing it only when first needed to avoid runtime errors during
    module imports.
    
    Returns:
        AIClientManager: The singleton instance
    """
    global _ai_manager
    
    if _ai_manager is None:
        with _manager_lock:
            # Double-check locking pattern
            if _ai_manager is None:
                _ai_manager = AIClientManager()
    
    return _ai_manager

# Convenience accessors for backward compatibility
def get_text_analysis_client() -> AsyncOpenAI:
    """Get dedicated client for text analysis services."""
    return get_ai_client_manager().get_text_analysis_client()

def get_facial_analysis_client() -> AsyncOpenAI:
    """Get dedicated client for facial analysis services."""
    return get_ai_client_manager().get_facial_analysis_client()

def get_conversation_client() -> AsyncOpenAI:
    """Get dedicated client for conversation services."""
    return get_ai_client_manager().get_conversation_client()

def get_transcription_client() -> AsyncOpenAI:
    """Get dedicated client for transcription services."""
    return get_ai_client_manager().get_transcription_client()