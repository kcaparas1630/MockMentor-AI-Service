from collections import deque
import time
import base64
from typing import Optional
from loguru import logger

class IncrementalAudioBuffer:
    """
    Optimized audio buffer that accumulates chunks and provides incremental transcription
    by transcribing only NEW chunks since the last incremental transcription.
    """
    
    def __init__(self, incremental_size_threshold: int = 5, final_timeout: float = 2.0):
        self.chunks = deque()
        self.incremental_size_threshold = incremental_size_threshold
        self.final_timeout = final_timeout
        self.last_chunk_time = None
        self.last_incremental_size = 0
        self.is_speaking = False
        
    def add_chunk(self, chunk_data: str, is_speaking: bool = True):
        """Add a chunk and update speaking state."""
        self.chunks.append(chunk_data)
        self.last_chunk_time = time.time()
        self.is_speaking = is_speaking
        
    def should_do_incremental_transcription(self) -> bool:
        """
        Determine if we should do incremental transcription.
        Only transcribe if we have accumulated enough NEW chunks.
        """
        current_size = len(self.chunks)
        if current_size >= self.last_incremental_size + self.incremental_size_threshold:
            return True
        return False
        
    def get_incremental_audio_data(self) -> Optional[str]:
        """
        Get combined audio data for incremental transcription.
        Returns only NEW chunks since the last incremental transcription.
        """
        if not self.chunks:
            return None
            
        try:
            # Only get chunks since the last incremental transcription
            new_chunks = list(self.chunks)[self.last_incremental_size:]
            
            if not new_chunks:
                return None
                
            logger.debug(f"Processing {len(new_chunks)} new chunks for incremental transcription")
            
            # Combine only the new chunks
            combined_data = b""
            for chunk in new_chunks:
                chunk_bytes = base64.b64decode(chunk)
                combined_data += chunk_bytes
            
            # Return as base64 for transcription
            return base64.b64encode(combined_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error combining new chunks for incremental transcription: {e}")
            return None
            
    def get_overlapping_audio_data(self, overlap_chunks: int = 2) -> Optional[str]:
        """
        Get audio data with some overlap from previous transcription.
        This helps ensure we don't miss words at chunk boundaries.
        """
        if not self.chunks:
            return None
            
        try:
            # Include some overlap from previous transcription to avoid missing words
            start_idx = max(0, self.last_incremental_size - overlap_chunks)
            chunks_to_process = list(self.chunks)[start_idx:]
            
            if not chunks_to_process:
                return None
                
            logger.debug(f"Processing {len(chunks_to_process)} chunks with overlap for incremental transcription")
            
            # Combine chunks with overlap
            combined_data = b""
            for chunk in chunks_to_process:
                chunk_bytes = base64.b64decode(chunk)
                combined_data += chunk_bytes
            
            # Return as base64 for transcription
            return base64.b64encode(combined_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error combining overlapping chunks for incremental transcription: {e}")
            return None
            
    def mark_incremental_transcription_done(self):
        """Mark that incremental transcription was done at current size."""
        self.last_incremental_size = len(self.chunks)
        
    def should_do_final_transcription(self) -> bool:
        """
        Determine if we should do final transcription.
        This happens when speech ends or after a timeout.
        """
        if not self.is_speaking and self.chunks:
            return True
            
        # Also check for timeout
        if (self.last_chunk_time and 
            time.time() - self.last_chunk_time >= self.final_timeout and 
            len(self.chunks) > self.last_incremental_size):
            return True
            
        return False
        
    def get_final_audio_data(self) -> Optional[str]:
        """Get all audio data for final transcription."""
        if not self.chunks:
            return None
            
        try:
            # Combine all chunks into a single base64 string
            combined_data = b""
            for chunk in self.chunks:
                chunk_bytes = base64.b64decode(chunk)
                combined_data += chunk_bytes
            
            return base64.b64encode(combined_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error combining chunks for final transcription: {e}")
            return None
        
    def clear(self):
        """Clear all chunks and reset state."""
        self.chunks.clear()
        self.last_incremental_size = 0
        self.last_chunk_time = None
        
    def has_chunks(self) -> bool:
        """Check if there are any chunks in the buffer."""
        return bool(self.chunks)
