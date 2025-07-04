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
import time

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
        start_time = time.time()
        
        # Decode timing
        decode_start = time.time()
        audio_bytes = base64.b64decode(base64_data)
        logger.info(f"Decode time: {time.time() - decode_start:.2f}s")
        
        # File I/O timing
        io_start = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name
        logger.info(f"File I/O time: {time.time() - io_start:.2f}s")
        
        try:
            # Transcription timing
            transcribe_start = time.time()
            segments, _ = self.model.transcribe(temp_path)
            transcribe_text = " ".join([seg.text for seg in segments])
            logger.info(f"Transcription time: {time.time() - transcribe_start:.2f}s")
            
            logger.info(f"Total time: {time.time() - start_time:.2f}s")
            return transcribe_text
        finally:
            os.unlink(temp_path)
