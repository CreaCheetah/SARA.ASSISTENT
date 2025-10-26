from abc import ABC, abstractmethod
from pathlib import Path

class TTSPort(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Zet tekst om naar spraakbestand."""
        pass
