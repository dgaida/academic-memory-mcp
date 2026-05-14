"""Modul zum Parsen von PDF-Dokumenten."""
import logging
from pathlib import Path
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)

class PDFParser:
    """Parser für PDF- und DOCX-Dokumente mittels MinerU."""

    def __init__(self, cache_dir: Path):
        """Initialisiert den PDF-Parser.

        Args:
            cache_dir: Verzeichnis für temporäre Dateien.
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_magic_pdf_config()

    def _ensure_magic_pdf_config(self) -> None:
        """Initialisiert die MinerU-Konfiguration falls nicht vorhanden."""
        config_path = Path.home() / "magic-pdf.json"
        if not config_path.exists():
            logger.info("Initializing magic-pdf config...")
            try:
                subprocess.run(["cp-config"], capture_output=True)
            except FileNotFoundError:
                logger.warning("cp-config not found. Skipping magic-pdf config initialization. Ensure magic-pdf[full] is installed: pip install magic-pdf[full]")

    def parse(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer PDF- oder DOCX-Datei.

        Args:
            file_path: Pfad zur Datei.

        Returns:
            Extrahierter Text.
        """
        if file_path.suffix.lower() == ".docx":
            return self._parse_docx(file_path)

        try:
            # MinerU CLI call
            subprocess.run([
                "magic-pdf", "pdf-extract", "--pdf", str(file_path),
                "--output-dir", str(self.cache_dir)
            ], capture_output=True, check=True)

            # Find the generated markdown
            md_path = self.cache_dir / f"{file_path.stem}.md"
            if md_path.exists():
                return md_path.read_text(encoding="utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")

        return None

    def _parse_docx(self, path: Path) -> Optional[str]:
        """Parsen von DOCX als Fallback."""
        try:
            import docx
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error parsing DOCX {path}: {e}")
            return None

def get_parser(cache_dir: Path) -> PDFParser:
    """Liefert eine Parser-Instanz.

    Args:
        cache_dir: Cache-Verzeichnis.

    Returns:
        PDFParser: Instanz des Parsers.
    """
    return PDFParser(cache_dir)
