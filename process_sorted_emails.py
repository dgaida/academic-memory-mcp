"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""

import argparse
import logging
import sys
import gradio as gr
from pathlib import Path
from datetime import datetime

from mcp_university.config import get_config
from mcp_university.classifier.controller import EmailController

# Globaler Logger
logger = logging.getLogger(__name__)

DEBUG = True

def run_gradio_gui(controller: EmailController, report_path: Path):
    """Startet die Gradio GUI zur Korrektur der Einsortierung.

    Args:
        controller: EmailController Instanz.
        report_path: Pfad zum sorted_emails.md Report.
    """
    emails = controller.parse_report(report_path)
    if not emails:
        logger.info("Keine E-Mails zum Anzeigen im Gradio GUI.")
        return

    available_classes = sorted([c for c in controller.class_paths.keys() if c != "Other"])
    if "Others" not in available_classes:
        available_classes.append("Others")

    with gr.Blocks(title="E-Mail Sortierung Überprüfung") as demo:
        gr.Markdown("# E-Mail Sortierung Überprüfung")
        gr.Markdown("Bitte kontrollieren Sie die automatisch vorgenommene Einsortierung.")

        dropdowns = []
        email_data = []

        for mail in emails:
            with gr.Group():
                with gr.Row():
                    with gr.Column(scale=4):
                        gr.Markdown(
                            f"**Student:** {mail['lastname']} ({mail['semester']}) | **Ordner:** {mail['folder']}\n**Datei:** `{mail['path'].name}`"
                        )
                    with gr.Column(scale=1):
                        initial_value = mail["class"]
                        if initial_value == "Other":
                            initial_value = "Others"

                        dd = gr.Dropdown(
                            choices=available_classes,
                            value=initial_value,
                            label="Korrektes Ziel",
                        )
                        dropdowns.append(dd)
                        email_data.append(mail)

        with gr.Row():
            btn = gr.Button("Mails neu einsortieren", variant="primary")
            status_out = gr.Textbox(label="Ergebnis")

        def handle_click(*selected_classes):
            changes = []
            for mail, new_class in zip(email_data, selected_classes):
                m = mail.copy()
                m["new_class"] = new_class
                changes.append(m)

            try:
                controller.relocate_emails(changes)
                return "Verarbeitung abgeschlossen. Mails wurden ggf. verschoben und Ordner bereinigt."
            except Exception as e:
                logger.exception("Fehler bei Relokation")
                return f"Fehler: {str(e)}"

        btn.click(handle_click, inputs=dropdowns, outputs=status_out)

    demo.launch(inbrowser=True)

def valid_date(s: str) -> datetime:
    """Parses a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = f"Invalid date format: '{s}'. Expected format: YYYY-MM-DD."
        raise argparse.ArgumentTypeError(msg)

def main() -> None:
    """Haupteinstiegspunkt des Skripts."""
    config = get_config()
    config.log_path.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(config.log_path / "process_emails.log", encoding="utf-8"),
            logging.StreamHandler()
        ],
        force=True,
    )

    parser = argparse.ArgumentParser(description="Verarbeitet sortierte E-Mails und generiert Antworten.")
    parser.add_argument("source_dir", help="Quellordner der E-Mails")
    parser.add_argument("--config", default="config/folders.yaml", help="Pfad zur Konfiguration")
    parser.add_argument("--debug", action="store_true", default=DEBUG, help="Speichert LLM Prompts (Default: True)")
    parser.add_argument("--no-debug", action="store_false", dest="debug", help="Deaktiviert das Speichern von Prompts")
    parser.add_argument("--use-mcp", action="store_true", help="Nutzt den MCP Server für Tools")
    parser.add_argument("--use-cloud", action="store_true", help="Nutzt ein Cloud-LLM")
    parser.add_argument("--cloud-provider", default="openai", help="Cloud-LLM Provider")
    parser.add_argument("--cloud-model", default="gpt-4o", help="Cloud-LLM Modell")
    parser.add_argument("--api-key", help="Cloud-LLM API-Key")
    parser.add_argument("--method", default="transformer", help="Klassifizierungsmethode")
    parser.add_argument("--mode", default="combined", help="Merkmalsextraktion")
    parser.add_argument("--age-months", type=int, help="E-Mails älter als X Monate werden nur einsortiert.")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)

    controller = EmailController(
        config_path=args.config,
        use_mcp=args.use_mcp,
        use_cloud=args.use_cloud,
        cloud_provider=args.cloud_provider,
        cloud_model=args.cloud_model,
        api_key=args.api_key,
        debug=args.debug
    )

    # 1. Sortieren
    try:
        controller.run_sort(str(source_dir), method=args.method, mode=args.mode)
    except Exception as e:
        logger.error(f"Fehler beim Sortieren: {e}")
        sys.exit(1)

    # 2. Verarbeiten
    controller.process_all_emails(source_dir, age_months=args.age_months)

    # 3. Gradio GUI
    try:
        run_gradio_gui(controller, source_dir / "sorted_emails.md")
    except Exception as e:
        logger.error(f"Fehler beim Starten der Gradio GUI: {e}")

if __name__ == "__main__":
    main()
