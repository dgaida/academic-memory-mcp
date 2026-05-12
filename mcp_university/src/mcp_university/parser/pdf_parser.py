from pathlib import Path
from typing import Optional
import logging
import subprocess
import shutil
import docx

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, file_path: Path) -> Optional[str]:
        """
        Parses a PDF or DOCX file.
        Uses magic-pdf for PDF if possible.
        Uses python-docx for DOCX as fallback if magic-pdf fails (e.g. no LibreOffice).
        """
        try:
            if file_path.suffix.lower() == ".docx":
                return self._parse_docx(file_path)

            # For PDF
            file_name_stem = file_path.stem
            result = subprocess.run([
                "magic-pdf",
                "-p", str(file_path),
                "-o", str(self.output_dir),
                "-m", "auto"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                possible_path = self.output_dir / file_name_stem / "auto" / f"{file_name_stem}.md"
                if possible_path.exists():
                    return possible_path.read_text(encoding="utf-8")

            # If magic-pdf fails or not a PDF/DOCX it supports well without extra deps
            # Just return basic text extraction for now if it's a PDF but magic-pdf failed
            logger.warning(f"magic-pdf failed for {file_path}, return None")
            return None

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _parse_docx(self, file_path: Path) -> str:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text)

def get_parser(output_dir: Path) -> PDFParser:
    return PDFParser(output_dir)
