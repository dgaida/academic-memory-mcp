"""Modul zum Parsen von PDF-Dokumenten mittels Docling."""
import logging
import warnings
from pathlib import Path
from typing import Optional
from docling.document_converter import DocumentConverter
from mcp_university.config import get_config

# Suppress torch pin_memory warnings when no accelerator is found
warnings.filterwarnings("ignore", message=".*pin_memory.*")

logger = logging.getLogger(__name__)

class PDFParser:
    """Parser für PDF- und DOCX-Dokumente mittels Docling."""

    def __init__(self, cache_dir: Path):
        """Initialisiert den PDF-Parser.

        Args:
            cache_dir: Verzeichnis für temporäre Dateien (für Docling nicht zwingend nötig, bleibt für Kompatibilität).
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        config = get_config()
        if config.offline:
            # Im Offline-Modus setzen wir Umgebungsvariablen, die Docling/Transformers beeinflussen
            # Docling nutzt intern oft Hugging Face Modelle.
            import os
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

        self.converter = DocumentConverter()

    def parse(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer PDF- oder DOCX-Datei mittels Docling.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Extrahierter Text im Markdown-Format.
        """
        logger.info(f"Parsing document with docling: {file_path}")
        try:
            # Limit processing to first 3 pages
            result = self.converter.convert(str(file_path), max_num_pages=3)

            # Some versions might use result.document.export_to_markdown()
            markdown = result.document.export_to_markdown()
            return markdown
        except Exception as e:
            logger.error(f"Error parsing document {file_path} with docling: {e}")
            # Fallback for docx if docling fails
            if file_path.suffix.lower() == ".docx":
                return self._parse_docx_fallback(file_path)
            return None

    def _parse_docx_fallback(self, path: Path) -> Optional[str]:
        """Parsen von DOCX als Fallback mittels python-docx."""
        try:
            import docx
            logger.info(f"Parsing DOCX (Fallback): {path}")
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error parsing DOCX {path} (Fallback): {e}")
            return None

def get_parser(cache_dir: Path) -> PDFParser:
    """Liefert eine Parser-Instanz.

    Args:
        cache_dir: Cache-Verzeichnis.

    Returns:
        PDFParser: Instanz des Parsers.
    """
    return PDFParser(cache_dir)
