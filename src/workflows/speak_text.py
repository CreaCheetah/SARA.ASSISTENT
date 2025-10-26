from pathlib import Path
from tempfile import NamedTemporaryFile
from src.adapters.openai_tts import OpenAITTSAdapter

tts = OpenAITTSAdapter()

def speak_text(text: str) -> bytes:
    with NamedTemporaryFile(delete=True, suffix=".mp3") as tmp:
        tts.synthesize(text, Path(tmp.name))
        return tmp.read()
