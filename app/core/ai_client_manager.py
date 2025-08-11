"""
AI Client Manager

This module manages separate AI client instances for different services to prevent
API contention and improve performance. Each service type gets its own dedicated
client instance.
"""

import os
from openai import AsyncOpenAI
import logging
from typing import Dict
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
    
    _instance = None
    _clients: Dict[str, AsyncOpenAI] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIClientManager, cls).__new__(cls)
            cls._instance._initialize_clients()
        return cls._instance
    
    def _initialize_clients(self):
        """Initialize separate client instances for different services."""
        api_key = os.getenv("NEBIUS_API_KEY")
        if not api_key:
            raise RuntimeError("NEBIUS_API_KEY environment variable is not set")
        
        base_url = "https://api.studio.nebius.com/v1"
        
        # Create dedicated clients for different services
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
        
        logger.info(f"Initialized {len(self._clients)} dedicated AI client instances")
    
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
        """
        if service_type not in self._clients:
            available_types = list(self._clients.keys())
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

# Global instance
ai_client_manager = AIClientManager()