from faster_whisper import WhisperModel
import tempfile
import base64

_model = None

# Lazy load the model only when needed. 
# If transcription has problems in production, try to increase the cloud run memory allocation, or use tiny model.
def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model

def transcribe_base64_audio(base64_data: str) -> str:
    model = get_model();
    # Decode to audio
    audio_bytes = base64.b64decode(base64_data)

    # Save to file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name

    # Transcribe using faster-whisper
    segments, _ = model.transcribe(temp_path)
    return " ".join([seg.text for seg in segments])
