from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class AudioASRPort(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Zet audio om naar tekst."""
        pass
