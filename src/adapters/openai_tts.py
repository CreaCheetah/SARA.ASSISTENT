from pathlib import Path
import openai
from src.ports.tts import TTSPort
from src.infra.settings import settings

class OpenAITTSAdapter(TTSPort):
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def synthesize(self, text: str, output_path: Path) -> Path:
        response = openai.audio.speech.create(
            model=settings.TTS_MODEL,
            voice=settings.TTS_VOICE,
            input=text
        )
        response.stream_to_file(output_path)
        return output_path
