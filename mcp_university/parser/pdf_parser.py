from pathlib import Path
from typing import Optional
import logging
import subprocess
import shutil
import docx
import json
import os

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_magic_pdf_config()

    def _ensure_magic_pdf_config(self):
        """Ensures magic-pdf config exists."""
        config_path = Path.home() / ".magic-pdf.json"
        if not config_path.exists():
            logger.info("Initializing magic-pdf config...")
            config = {
                "device": "cpu",
                "models-dir": str(Path.home() / "magic-pdf-models"),
                "weights": {
                    "layout": "layoutlmv3",
                    "formula": "mfr",
                    "table": "tablemaster"
                }
            }
            try:
                config_path.write_text(json.dumps(config, indent=4))
            except Exception as e:
                logger.warning(f"Could not create magic-pdf config: {e}")

    def parse(self, file_path: Path) -> Optional[str]:
        """
        Parses a PDF or DOCX file.
        Uses magic-pdf (MinerU) for PDF if possible.
        Uses python-docx for DOCX as fallback.
        """
        try:
            if file_path.suffix.lower() == ".docx":
                return self._parse_docx(file_path)

            if file_path.suffix.lower() != ".pdf":
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return None

            # For PDF - use magic-pdf (MinerU)
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

                for md_file in (self.output_dir / file_name_stem).rglob("*.md"):
                    return md_file.read_text(encoding="utf-8")

            logger.warning(f"magic-pdf failed for {file_path}. Output: {result.stderr}")
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
