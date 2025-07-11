"""
Description:
This module provides functionality to transcribe audio data encoded in base64 format using the Faster Whisper model
Dependencies:
- faster-whisper: For audio transcription.
- tempfile: For creating temporary files.
- base64: For decoding base64 audio data.
Authors: @kcaparas1630
         @William226
"""
from faster_whisper import WhisperModel
import tempfile
import base64
from loguru import logger
import os

_model = None

class TranscriberService:
    def __init__(self):
        self.model = self.get_model()
    
    def get_model(self):
        """
        Initializes and returns the WhisperModel instance.
        This function ensures that the model is loaded only once and reused for subsequent calls.
       
        Returns:
            WhisperModel: An instance of the WhisperModel configured for transcription.
        """
        global _model
        if _model is None:
            _model = WhisperModel("base.en", device="cpu", compute_type="int8", num_workers=1, cpu_threads=4)
        return _model
    
    def transcribe_base64_audio(self, base64_data: str) -> str:
        """
        Transcribes base64 encoded audio data (WebM/Opus format) to text.
        
        Args:
            base64_data (str): Base64 encoded audio data in WebM/Opus format
            
        Returns:
            str: Transcribed text from the audio
        """
        try:
            audio_bytes = base64.b64decode(base64_data)
            logger.debug(f"Decoded audio data, size: {len(audio_bytes)} bytes")
            
            # Use .webm extension for WebM/Opus format
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name
            
            logger.debug(f"Created temporary file: {temp_path}")
            
            segments, _ = self.model.transcribe(
                temp_path,
                beam_size=7,
                best_of=1,
                temperature=0,
                vad_filter=True,
                word_timestamps=False,
                condition_on_previous_text=False
            )
            
            transcribe_text = " ".join([seg.text for seg in segments])
            return transcribe_text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise
        finally:
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
            except OSError as e:
                logger.warning(f"Error removing temporary file {temp_path}: {str(e)}")
