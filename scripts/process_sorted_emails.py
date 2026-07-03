"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""

import argparse
import os
import subprocess
import platform
import logging
import sys
import shutil
import gradio as gr
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from mcp_university.config import get_config
from email_classifier.controller import EmailController

# Globaler Logger
logger = logging.getLogger(__name__)

DEBUG = True

def run_gradio_gui(controller: EmailController, source_dir: Path, method: str = "transformer", mode: str = "combined", age_months: int = None):
    """Startet die Gradio GUI zur Korrektur der Einsortierung mit zwei Tabs.

    Args:
        controller: EmailController Instanz.
        source_dir: Quellverzeichnis der E-Mails.
        method: Klassifizierungsmethode.
        mode: Merkmalsextraktion.
        age_months: Alter der E-Mails in Monaten.
    """

    available_classes = sorted([c for c in controller.class_paths.keys() if c != "Other"])
    if "Others" not in available_classes:
        available_classes.append("Others")

    with gr.Blocks(title="E-Mail Management") as demo:
        gr.Markdown("# E-Mail Management")

        # States for the two tabs
        tab1_mails = gr.State([])
        tab2_mails = gr.State([])

        with gr.Tabs() as tabs:
            with gr.Tab("Schnell-Einsortierung", id=0):
                gr.Markdown("E-Mails in `D:\\TH_Koeln\\StudentMails` klassifizieren.")

                with gr.Row():
                    scan_btn = gr.Button("E-Mails scannen & klassifizieren", variant="primary")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Inbox")
                        inbox_list = gr.Dataframe(
                            headers=["Index", "Klasse", "Student", "Datei"],
                            datatype=["number", "str", "str", "str"],
                            interactive=False,
                            label="Inbox Mails"
                        )
                    with gr.Column():
                        gr.Markdown("### SentItems")
                        sent_list = gr.Dataframe(
                            headers=["Index", "Klasse", "Student", "Datei"],
                            datatype=["number", "str", "str", "str"],
                            interactive=False,
                            label="SentItems Mails"
                        )

                with gr.Row():
                    remove_idx = gr.Number(label="Index zum Entfernen", precision=0)
                    remove_btn = gr.Button("Markierte Mail nach Tab 2 schieben")

                with gr.Row():
                    relocate_btn = gr.Button("Verbleibende Mails archivieren", variant="primary")
                    tab1_status = gr.Textbox(label="Status")

            with gr.Tab("Detail-Ansicht & Verarbeitung", id=1):
                gr.Markdown("Hier können Mails detailliert geprüft und verarbeitet werden.")

                @gr.render(inputs=tab2_mails)
                def render_tab2(mails):
                    if not mails:
                        gr.Markdown("Keine Mails zur Detail-Ansicht.")
                        return

                    dropdowns = []
                    action_dropdowns = []
                    checkboxes = []

                    for mail in mails:
                        with gr.Group():
                            mail_path = Path(mail["path"])

                            summary = controller.generate_short_summary(mail_path)
                            similarity_info = controller.get_similarity_info(mail_path, mail["lastname"])

                            gr.Markdown(
                                f"**Student:** {mail['lastname']} | **Klasse:** {mail['class']}\n"
                                f"**Datei:** `{mail_path.name}`\n\n"
                                f"*Zusammenfassung:* {summary}\n\n"
                                f"{similarity_info}"
                            )

                            with gr.Row():
                                dd = gr.Dropdown(choices=available_classes, value=mail["class"], label="Korrektes Ziel")
                                dropdowns.append(dd)

                                action_val = controller.ACTION_OPTIONS[0]
                                action_dd = gr.Dropdown(choices=controller.ACTION_OPTIONS, value=action_val, label="Aktion")
                                action_dropdowns.append(action_dd)

                                att_cb = gr.Checkbox(label="Anhang speichern", value=False)
                                checkboxes.append(att_cb)

                    process_btn = gr.Button("Mails in Tab 2 verarbeiten", variant="primary")
                    tab2_status_local = gr.Textbox(label="Status")

                    def handle_tab2_process(*args):
                        num = len(mails)
                        sels = args[:num]
                        acts = args[num:2*num]
                        atts = args[2*num:]

                        processed_list = []
                        for i, m in enumerate(mails):
                            change = m.copy()
                            change["new_class"] = sels[i]
                            change["save_attachments"] = atts[i]
                            processed_list.append((change, acts[i]))

                        # 1. Relocate
                        rel_changes = [p[0] for p in processed_list]
                        errors = controller.relocate_emails(rel_changes)

                        # 2. Actions
                        results = []
                        for change, act_str in processed_list:
                            try:
                                action_idx = controller.ACTION_OPTIONS.index(act_str)
                                current_path = change.get("new_path") or change["path"]
                                res = controller.execute_action(action_idx, current_path, change)
                                results.append(f"{change['lastname']}: {res}")
                            except Exception as e:
                                results.append(f"{change['lastname']}: Fehler {str(e)}")

                        msg = "Verarbeitung abgeschlossen."
                        if errors: msg += "\nFehler: " + "; ".join(errors)
                        if results: msg += "\nAktionen:\n" + "\n".join(results)
                        return msg

                    process_btn.click(
                        handle_tab2_process,
                        inputs=dropdowns + action_dropdowns + checkboxes,
                        outputs=tab2_status_local
                    )

        def scan_emails():
            try:
                results = controller.run_sort(str(source_dir), method=method, mode=mode, dry_run=True)
                inbox = []
                sent = []
                for i, res in enumerate(results):
                    row = [i, res["class"], res["lastname"], Path(res["path"]).name]
                    if res["folder"] == "Inbox":
                        inbox.append(row)
                    else:
                        sent.append(row)
                return results, [], inbox, sent, f"{len(results)} Mails gefunden."
            except Exception as e:
                logger.exception("Fehler beim Scannen")
                return [], [], [], [], f"Fehler: {str(e)}"

        scan_btn.click(
            scan_emails,
            outputs=[tab1_mails, tab2_mails, inbox_list, sent_list, tab1_status]
        )

        def remove_to_tab2(idx, t1_mails, t2_mails):
            if not t1_mails or idx is None or idx < 0 or idx >= len(t1_mails):
                return t1_mails, t2_mails, gr.update(), gr.update(), "Ungültiger Index"

            mail_to_move = t1_mails.pop(int(idx))
            t2_mails.append(mail_to_move)

            inbox = []
            sent = []
            for i, res in enumerate(t1_mails):
                row = [i, res["class"], res["lastname"], Path(res["path"]).name]
                if res["folder"] == "Inbox":
                    inbox.append(row)
                else:
                    sent.append(row)

            return t1_mails, t2_mails, inbox, sent, f"Mail {mail_to_move['lastname']} nach Tab 2 verschoben."

        remove_btn.click(
            remove_to_tab2,
            inputs=[remove_idx, tab1_mails, tab2_mails],
            outputs=[tab1_mails, tab2_mails, inbox_list, sent_list, tab1_status]
        )

        def relocate_remaining(t1_mails):
            if not t1_mails:
                return [], [], [], "Keine Mails zum Verschieben."

            changes = []
            for m in t1_mails:
                change = m.copy()
                change["new_class"] = m["class"]
                changes.append(change)

            try:
                errors = controller.relocate_emails(changes)
                if errors:
                    return t1_mails, gr.update(), gr.update(), "Fehler beim Verschieben: " + "; ".join(errors)
                return [], [], [], "Mails erfolgreich archiviert."
            except Exception as e:
                return t1_mails, gr.update(), gr.update(), f"Fehler: {str(e)}"

        relocate_btn.click(
            relocate_remaining,
            inputs=[tab1_mails],
            outputs=[tab1_mails, inbox_list, sent_list, tab1_status]
        )

    demo.launch(inbrowser=True)

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
    parser.add_argument("--no-action-classifier", action="store_false", dest="use_action_classifier", default=True, help="Deaktiviert den neuen Aktions-Klassifizierer")
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
        debug=args.debug, use_action_classifier=args.use_action_classifier
    )

    try:
        run_gradio_gui(controller, source_dir, method=args.method, mode=args.mode, age_months=args.age_months)
    except Exception as e:
        logger.error(f"Fehler beim Starten der Gradio GUI: {e}")

if __name__ == "__main__":
    main()
