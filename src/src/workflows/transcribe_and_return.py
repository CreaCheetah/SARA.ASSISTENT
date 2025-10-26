from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from src.adapters.openai_asr import OpenAIWhisperAdapter

asr = OpenAIWhisperAdapter()

def transcribe_bytes(data: bytes, suffix: str = ".wav", language: Optional[str] = "nl") -> str:
    with NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(data)
        tmp.flush()
        return asr.transcribe(Path(tmp.name), language=language)
