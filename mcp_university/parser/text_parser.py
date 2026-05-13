"""Parser für einfache Textformate."""
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class TextParser:
    """Parser für einfache Textformate wie .txt, .md, .py."""

    def parse(self, file_path: Path) -> Optional[str]:
        """Liest den Inhalt einer Textdatei.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Dateiinhalt als String oder None.
        """
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
