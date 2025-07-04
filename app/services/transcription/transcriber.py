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
            _model = WhisperModel("base", device="cpu", compute_type="int8")
        return _model

    def transcribe_base64_audio(self, base64_data: str) -> str:
        """
        Transcribes audio data encoded in base64 format to text.
        Args:
            base64_data (str): Base64 encoded audio data.
        Returns:
        str: Transcribed text from the audio data.
    """
        model = self.get_model()
        # Decode to audio
        audio_bytes = base64.b64decode(base64_data)

        # Save to file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name
        try:
            # Transcribe using faster-whisper
            segments, _ = model.transcribe(temp_path)
            return " ".join([seg.text for seg in segments])
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError as e:
                logger.error(f"Error removing temporary file {temp_path}: {e}")
