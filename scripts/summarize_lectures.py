"""Skript zur Zusammenfassung von Vorlesungsfolien (PDFs) mittels LLM."""
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from llm_client import LLMClient
from mcp_university.parser.pdf_parser import PDFParser

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="Fasst PDF-Vorlesungsfolien mittels LLM zusammen.")

PROMPT_TEMPLATE = """
Du bist ein Assistent für eine akademische Wissensdatenbank.
Deine Aufgabe ist es, die bereitgestellten Vorlesungsfolien zusammenzufassen.
Bitte extrahiere die folgenden Informationen aus dem Text:

- Name der Hochschule
- Name des Moduls
- Name des Lehrenden oder der Lehrenden
- Semester
- Thema der Vorlesung
- Die wichtigsten 5 Keyfacts als Bulletpoints

Antworte im Markdown-Format. Wenn eine Information nicht im Text gefunden werden kann, schreibe "Nicht angegeben".

Hier ist der Text der Folien:
---
{content}
---
"""

def summarize_pdf(pdf_path: Path, client: LLMClient, parser: PDFParser) -> Optional[str]:
    """Extrahiert Text aus einem PDF und lässt ihn vom LLM zusammenfassen."""
    logger.info(f"Verarbeite: {pdf_path.name}")

    content = parser.parse(pdf_path)
    if not content:
        logger.error(f"Konnte Text aus {pdf_path} nicht extrahieren.")
        return None

    messages = [
        {"role": "system", "content": "Du bist ein hilfreicher akademischer Assistent."},
        {"role": "user", "content": PROMPT_TEMPLATE.format(content=content)}
    ]

    try:
        response = client.chat_completion(messages)
        return response
    except Exception as e:
        logger.error(f"Fehler bei der LLM-Anfrage für {pdf_path}: {e}")
        return None

@app.command()
def main(
    source_dir: Path = typer.Argument(..., help="Ordner mit den PDF-Dateien"),
    target_dir: Path = typer.Argument(..., help="Zielordner für die Markdown-Zusammenfassungen"),
    api_choice: str = typer.Option("gemini", help="LLM Provider (z.B. gemini, openai, groq, ollama)"),
    model: Optional[str] = typer.Option(None, help="Spezifisches Modell (Standard: Provider-Default)"),
):
    """Geht alle PDFs im Quellordner durch und erstellt Zusammenfassungen im Zielordner."""

    if not source_dir.is_dir():
        logger.error(f"Quellverzeichnis existiert nicht: {source_dir}")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    # PDF Parser initialisieren
    parser = PDFParser(cache_dir=Path("data/cache"))

    # LLM Client initialisieren
    # api_choice in LLMClient erwartet Literal['openai', 'groq', 'gemini', 'ollama']
    client = LLMClient(api_choice=api_choice, llm=model)

    pdf_files = list(source_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info(f"Keine PDF-Dateien in {source_dir} gefunden.")
        return

    logger.info(f"Gefunden: {len(pdf_files)} PDFs. Starte Verarbeitung...")

    for pdf_path in pdf_files:
        summary = summarize_pdf(pdf_path, client, parser)
        if summary:
            target_path = target_dir / f"{pdf_path.stem}.md"
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Zusammenfassung gespeichert in: {target_path}")

if __name__ == "__main__":
    app()
