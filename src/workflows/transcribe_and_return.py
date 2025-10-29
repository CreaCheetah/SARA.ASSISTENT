# src/workflows/transcribe_and_return.py
from __future__ import annotations
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from src.adapters.openai_asr import OpenAIWhisperAdapter

asr = OpenAIWhisperAdapter()

def transcribe_bytes(data: bytes, suffix: str = ".wav", language: Optional[str] = "nl") -> str:
    """Hulpfunctie: schrijf bytes naar tijdelijk bestand en transcribeer."""
    with NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(data)
        tmp.flush()
        return asr.transcribe(Path(tmp.name), language=language)

def transcribe_and_return(audio_bytes: bytes, content_type: str) -> str:
    """Entry point voor ai_routes.py. Bepaalt bestands-suffix uit content-type en retourneert tekst."""
    ct = (content_type or "").lower()
    if "wav" in ct:
        suffix = ".wav"
    elif "mpeg" in ct or "mp3" in ct:
        suffix = ".mp3"
    elif "ogg" in ct or "opus" in ct:
        suffix = ".ogg"
    elif "m4a" in ct or "mp4" in ct or "aac" in ct:
        suffix = ".m4a"
    else:
        suffix = ".wav"
    return transcribe_bytes(audio_bytes, suffix=suffix, language="nl")
