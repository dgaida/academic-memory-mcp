"""Parser-Fabrik zur Bereitstellung des passenden Parsers."""

from pathlib import Path
from typing import Optional
from .pdf_parser import PDFParser
from .text_parser import TextParser
from .mail_parser import MailParser


class ParserFactory:
    """Factory-Klasse zur Bereitstellung des passenden Parsers für verschiedene Dateitypen."""

    def __init__(self, cache_dir: Path):
        """Initialisiert die Factory mit den unterstützten Parsern.

        Args:
            cache_dir (Path): Verzeichnis für PDF-Parsing-Artefakte.
        """
        self.pdf_parser = PDFParser(cache_dir)
        self.text_parser = TextParser()
        self.mail_parser = MailParser()

    def parse(self, file_path: Path) -> Optional[str]:
        """Wählt den passenden Parser basierend auf der Dateiendung und extrahiert den Text.

        Args:
            file_path (Path): Pfad zur Datei.

        Returns:
            Optional[str]: Der extrahierte Text oder None.
        """
        suffix = file_path.suffix.lower()
        if suffix in [".pdf", ".docx"]:
            return self.pdf_parser.parse(file_path)
        elif suffix in [".txt", ".md", ".py", ".json", ".html", ".ipynb"]:
            return self.text_parser.parse(file_path)
        elif suffix in [".eml", ".msg"]:
            return self.mail_parser.parse(file_path)
        return None
