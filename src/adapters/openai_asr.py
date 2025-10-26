import openai
from pathlib import Path
from typing import Optional
from src.ports.audio_asr import AudioASRPort
from src.infra.settings import settings

class OpenAIWhisperAdapter(AudioASRPort):
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language or "nl"
            )
        return transcript.text
