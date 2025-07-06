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
            _model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return _model
    
    def transcribe_base64_audio(self, base64_data: str) -> str:
       
        audio_bytes = base64.b64decode(base64_data)       
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name       
        try:
            segments, _ = self.model.transcribe(
                temp_path,
                beam_size=1,
                best_of=1,
                temperature=0,
                vad_filter=True,
                word_timestamps=False,
                condition_on_previous_text=False
            )
            transcribe_text = " ".join([seg.text for seg in segments])
            logger.info(f"Transcribed text: {transcribe_text}")
            return transcribe_text
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning(f"Error removing temporary file {temp_path}")
