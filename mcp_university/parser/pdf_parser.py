"""Modul zum Parsen von PDF-Dokumenten mittels LiteParse mit Fallback auf Docling."""
import logging
import warnings
from pathlib import Path
from typing import Optional

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None

try:
    from liteparse import LiteParse
except ImportError:
    LiteParse = None

from mcp_university.config import get_config

# Suppress torch pin_memory warnings when no accelerator is found
warnings.filterwarnings("ignore", message=".*pin_memory.*")

logger = logging.getLogger(__name__)

class PDFParser:
    """Parser für PDF- und DOCX-Dokumente mittels Docling und LiteParse."""

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

        self.converter = DocumentConverter() if DocumentConverter else None
        self._lite_parser = None

    def parse(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer PDF- oder DOCX-Datei.

        Probiert zuerst LiteParse, dann Docling als Fallback für PDFs.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Extrahierter Text im Markdown-Format oder None.
        """
        # 1. Versuch mit LiteParse für PDFs
        if file_path.suffix.lower() == ".pdf":
            content = self._parse_with_liteparse(file_path)
            if content:
                return content

        # 2. Versuch mit Docling
        if self.converter:
            logger.info(f"Parsing document with docling: {file_path}")
            try:
                # Limit processing to first 3 pages
                result = self.converter.convert(str(file_path), max_num_pages=3)
                markdown = result.document.export_to_markdown()
                if markdown and len(markdown.strip()) > 0:
                    return markdown
                logger.warning(f"Docling returned empty content for {file_path}")
            except Exception as e:
                logger.error(f"Error parsing document {file_path} with docling: {e}")

        # 3. Fallback für DOCX
        if file_path.suffix.lower() == ".docx":
            return self._parse_docx_fallback(file_path)

        return None

    def _parse_with_liteparse(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer PDF-Datei mittels LiteParse als Fallback."""
        if not LiteParse:
            logger.error("LiteParse is not installed. Cannot use as fallback.")
            return None

        logger.info(f"Parsing document with liteparse (Fallback): {file_path}")
        try:
            if self._lite_parser is None:
                self._lite_parser = LiteParse()

            result = self._lite_parser.parse(str(file_path))
            # LiteParse result typically has .text
            if hasattr(result, "text"):
                return result.text
            return str(result)
        except Exception as e:
            logger.error(f"Error parsing document {file_path} with liteparse: {e}")
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
