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
            try:
                # Check if magic-pdf is available before trying to config
                subprocess.run(["magic-pdf", "-v"], capture_output=True, check=True)
                logger.info("Initializing magic-pdf config...")
                subprocess.run(["cp-config"], capture_output=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                logger.debug("magic-pdf config initialization skipped or failed.")

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
            # MinerU CLI call (using modern v1.x syntax)
            # Try new syntax first, then fallback to old if it fails with specific error
            result = subprocess.run([
                "magic-pdf", "-p", str(file_path),
                "-o", str(self.cache_dir)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                # Fallback to old syntax for older versions
                subprocess.run([
                    "magic-pdf", "pdf-extract", "--pdf", str(file_path),
                    "--output-dir", str(self.cache_dir)
                ], capture_output=True, check=True)

            # MinerU v1.x creates a directory with the file stem
            # and inside it puts the .md file and assets.
            # We look for the .md file in the output dir or its subdirs.

            # Check direct match (old style)
            md_path = self.cache_dir / f"{file_path.stem}.md"
            if md_path.exists():
                return md_path.read_text(encoding="utf-8")

            # Check subdir match (new style)
            # magic-pdf usually creates a folder named after the file
            potential_dir = self.cache_dir / file_path.stem
            if potential_dir.exists() and potential_dir.is_dir():
                md_files = list(potential_dir.glob("*.md"))
                if md_files:
                    # Return the largest md file or the one named after the stem
                    for f in md_files:
                        if f.stem == file_path.stem:
                            return f.read_text(encoding="utf-8")
                    return md_files[0].read_text(encoding="utf-8")

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
