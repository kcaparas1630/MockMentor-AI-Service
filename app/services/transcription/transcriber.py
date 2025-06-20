from faster_whisper import WhisperModel
import tempfile
import base64

# Load once globally
model = WhisperModel("base")

def transcribe_base64_audio(base64_data: str) -> str:
    # Decode to audio
    audio_bytes = base64.b64decode(base64_data)

    # Save to file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name

    # Transcribe using faster-whisper
    segments, _ = model.transcribe(temp_path)
    return " ".join([seg.text for seg in segments])