from openai import OpenAI
from pathlib import Path

class OpenAIWhisperAdapter:
    def __init__(self):
        self.client = OpenAI()

    def transcribe(self, audio_path: str, language: str = "nl") -> str:
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                language=language
            )
        return transcript.text
