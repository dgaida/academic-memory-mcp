"""Skript zur Verarbeitung sortierter E-Mails und Generierung von Antworten."""

import argparse
import logging
import os
import subprocess
import gradio as gr
from pathlib import Path
from typing import List, Dict, Any, Tuple, Generator, Union

from mcp_university.config import get_config
from email_classifier.controller import EmailController

# Globaler Logger
logger = logging.getLogger(__name__)

DEBUG = True

def run_gradio_gui(controller: EmailController, source_dir: Path, method: str = "transformer", mode: str = "combined", age_months: int = None) -> None:
    """Startet die Gradio GUI zur Korrektur der Einsortierung mit zwei Tabs.

    Args:
        controller (EmailController): EmailController Instanz.
        source_dir (Path): Quellverzeichnis der E-Mails.
        method (str): Klassifizierungsmethode. Defaults to "transformer".
        mode (str): Merkmalsextraktion. Defaults to "combined".
        age_months (int, optional): Alter der E-Mails in Monaten. Defaults to None.

    Returns:
        None
    """
    available_classes = sorted(list(controller.class_paths.keys()))

    def open_mail_fn(path: Union[str, Path]) -> str:
        """Öffnet eine E-Mail-Datei mit dem Standardprogramm des Betriebssystems.

        Args:
            path (Union[str, Path]): Pfad zur E-Mail-Datei.

        Returns:
            str: Statusmeldung über den Erfolg oder Fehler.
        """
        try:
            p = str(path)
            if os.name == 'nt':
                os.startfile(p)
            else:
                # macOS or Linux
                cmd = ['open', p] if os.uname().sysname == 'Darwin' else ['xdg-open', p]
                subprocess.run(cmd, check=False)
            return f"E-Mail geöffnet: {Path(p).name}"
        except Exception as e:
            logger.error(f"Fehler beim Öffnen der Mail {path}: {e}")
            return f"Fehler beim Öffnen der Mail: {e}"

    def open_folder_fn(path: Union[str, Path]) -> str:
        """Öffnet den Ordner einer Datei im Datei-Explorer.

        Args:
            path (Union[str, Path]): Pfad zur Datei.

        Returns:
            str: Statusmeldung über den Erfolg oder Fehler.
        """
        try:
            p = str(Path(path).parent)
            if os.name == 'nt':
                subprocess.run(['explorer', p], check=False)
            else:
                cmd = ['open', p] if os.uname().sysname == 'Darwin' else ['xdg-open', p]
                subprocess.run(cmd, check=False)
            return f"Ordner geöffnet: {p}"
        except Exception as e:
            logger.error(f"Fehler beim Öffnen des Ordners für {path}: {e}")
            return f"Fehler beim Öffnen des Ordners: {e}"

    with gr.Blocks(title="E-Mail Sortierung & Verarbeitung") as demo:
        # States
        tab1_mails = gr.State([])  # Alle aktuell in Tab 1 sichtbaren Mails
        tab2_mails = gr.State([])  # Mails, die in Tab 2 verarbeitet werden sollen

        gr.Markdown("# E-Mail Sortierung & Verarbeitung")

        with gr.Tabs() as tabs:
            with gr.Tab("Übersicht & Auswahl", id=0):
                gr.Markdown("Wähle die E-Mails aus, die du detailliert prüfen möchtest.")
                tab1_status = gr.Textbox(label="Status")

                @gr.render(inputs=tab1_mails)
                def render_tab1(mails: List[Dict[str, Any]]) -> None:
                    """Rendert die Übersicht der E-Mails in Tab 1."""
                    if not mails:
                        gr.Markdown("Keine Mails zum Verarbeiten.")
                        return

                    inbox_indices = [i for i, m in enumerate(mails) if m.get("folder") == "Inbox"]
                    sent_indices = [i for i, m in enumerate(mails) if m.get("folder") != "Inbox"]

                    checkboxes = []

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Posteingang")
                            for idx in inbox_indices:
                                mail = mails[idx]
                                with gr.Group():
                                    with gr.Row():
                                        cb = gr.Checkbox(label=f"{mail['lastname']} ({mail['class']})", value=False)
                                        checkboxes.append(cb)
                                        gr.Markdown(f"`{Path(mail['path']).name}`")
                                    with gr.Row():
                                        open_m_btn = gr.Button("📧 Öffnen", size="sm")
                                        open_f_btn = gr.Button("📂 Ordner", size="sm")
                                        open_m_btn.click(lambda p=mail["path"]: open_mail_fn(p), outputs=tab1_status)
                                        open_f_btn.click(lambda p=mail["path"]: open_folder_fn(p), outputs=tab1_status)

                        with gr.Column():
                            gr.Markdown("### Gesendete Elemente")
                            for idx in sent_indices:
                                mail = mails[idx]
                                with gr.Group():
                                    with gr.Row():
                                        cb = gr.Checkbox(label=f"{mail['lastname']} ({mail['class']})", value=False)
                                        checkboxes.append(cb)
                                        gr.Markdown(f"`{Path(mail['path']).name}`")
                                    with gr.Row():
                                        open_m_btn = gr.Button("📧 Öffnen", size="sm")
                                        open_f_btn = gr.Button("📂 Ordner", size="sm")
                                        open_m_btn.click(lambda p=mail["path"]: open_mail_fn(p), outputs=tab1_status)
                                        open_f_btn.click(lambda p=mail["path"]: open_folder_fn(p), outputs=tab1_status)

                    with gr.Row():
                        remove_btn = gr.Button("Markierte Mail nach Tab 2 schieben", variant="primary")
                        relocate_btn = gr.Button("Verbleibende Mails archivieren")

                    def handle_remove_to_tab2(t1_mails, t2_mails, *selected_states):
                        actual_selections = []
                        # Map states back to original indices
                        state_idx = 0
                        for idx in inbox_indices:
                            if selected_states[state_idx]:
                                actual_selections.append(idx)
                            state_idx += 1
                        for idx in sent_indices:
                            if selected_states[state_idx]:
                                actual_selections.append(idx)
                            state_idx += 1

                        if not actual_selections:
                            yield t1_mails, t2_mails, "Keine Mails ausgewählt.", gr.update()
                            return

                        yield from remove_to_tab2_logic(t1_mails, t2_mails, actual_selections)

                    remove_btn.click(
                        handle_remove_to_tab2,
                        inputs=[tab1_mails, tab2_mails] + checkboxes,
                        outputs=[tab1_mails, tab2_mails, tab1_status, tabs]
                    )

                    relocate_btn.click(
                        relocate_remaining,
                        inputs=[tab1_mails],
                        outputs=[tab1_mails, tab1_status]
                    )

            with gr.Tab("Detail-Ansicht & Verarbeitung", id=1):
                gr.Markdown("Hier können Mails detailliert geprüft und verarbeitet werden.")
                tab2_status_local = gr.Textbox(label="Status")

                @gr.render(inputs=tab2_mails)
                def render_tab2(mails: List[Dict[str, Any]]) -> None:
                    """Rendert die Detail-Ansicht für E-Mails in Tab 2."""
                    if not mails:
                        gr.Markdown("Keine Mails zur Detail-Ansicht.")
                        return

                    mails_snapshot = list(mails)
                    num_mails = len(mails_snapshot)

                    dropdowns = []
                    action_dropdowns = []
                    checkboxes = []

                    for mail in mails_snapshot:
                        with gr.Group():
                            mail_path = Path(mail["path"])

                            summary = mail.get("summary", "Wird geladen...")
                            similarity_info = mail.get("similarity_info", "")

                            gr.Markdown(
                                f"**Student:** {mail['lastname']} | **Klasse:** {mail['class']}\n"
                                f"**Datei:** `{mail_path.name}`\n\n"
                                f"*Zusammenfassung:* {summary}\n\n"
                                f"{similarity_info}"
                            )

                            with gr.Row():
                                open_m_btn = gr.Button("📧 E-Mail öffnen", size="sm")
                                open_f_btn = gr.Button("📂 Ordner öffnen", size="sm")

                                open_m_btn.click(lambda p=mail["path"]: open_mail_fn(p), outputs=tab2_status_local)
                                open_f_btn.click(lambda p=mail["path"]: open_folder_fn(p), outputs=tab2_status_local)

                            with gr.Row():
                                dd = gr.Dropdown(choices=available_classes, value=mail["class"], label="Korrektes Ziel", interactive=True)
                                dropdowns.append(dd)

                                action_val = mail.get("suggested_action", controller.ACTION_OPTIONS[0])
                                action_dd = gr.Dropdown(choices=controller.ACTION_OPTIONS, value=action_val, label="Aktion", interactive=True)
                                action_dropdowns.append(action_dd)

                                att_cb = gr.Checkbox(label="Anhang speichern", value=False)
                                checkboxes.append(att_cb)

                    process_btn = gr.Button("Mails in Tab 2 verarbeiten", variant="primary")

                    def handle_tab2_process(*args: Any) -> str:
                        num = num_mails
                        if len(args) < 3 * num:
                            return f"Fehler: Erwartete {3 * num} Argumente, erhielt {len(args)}."
                        sels = args[:num]
                        acts = args[num:2 * num]
                        atts = args[2 * num:3 * num]

                        processed_list = []
                        for i, m in enumerate(mails_snapshot):
                            change = m.copy()
                            change["new_class"] = sels[i]
                            change["save_attachments"] = atts[i]
                            processed_list.append((change, acts[i]))

                        errors = controller.relocate_emails([p[0] for p in processed_list])

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
                        if errors:
                            msg += "\nFehler: " + "; ".join(errors)
                        if results:
                            msg += "\nAktionen:\n" + "\n".join(results)
                        return msg

                    process_btn.click(
                        handle_tab2_process,
                        inputs=dropdowns + action_dropdowns + checkboxes,
                        outputs=tab2_status_local
                    )

        def scan_emails() -> Tuple[List[Dict[str, Any]], List[Any], str]:
            """Scannt das Quellverzeichnis nach E-Mails."""
            try:
                results = controller.run_sort(str(source_dir), method=method, mode=mode, dry_run=True)
                return results, [], f"{len(results)} Mails gefunden."
            except Exception as e:
                logger.exception("Fehler beim Scannen")
                return [], [], f"Fehler: {str(e)}"

        demo.load(scan_emails, outputs=[tab1_mails, tab2_mails, tab1_status])

        def remove_to_tab2_logic(t1_mails: List[Dict[str, Any]], t2_mails: List[Dict[str, Any]], selected_indices: List[int]) -> Generator:
            """Verschiebt markierte E-Mails von Tab 1 nach Tab 2 und startet die Verarbeitung."""
            selected_indices = sorted(list(set(selected_indices)), reverse=True)

            new_t1 = list(t1_mails)
            new_t2 = list(t2_mails)
            moved_this_session = []

            for idx in selected_indices:
                if 0 <= idx < len(new_t1):
                    mail = new_t1.pop(idx)
                    mail_copy = mail.copy()
                    mail_copy["summary"] = "Wird verarbeitet..."
                    mail_copy["similarity_info"] = "Suche ähnliche Mails..."
                    moved_this_session.append(mail_copy)

            current_t2 = new_t2 + moved_this_session

            yield new_t1, current_t2, f"{len(moved_this_session)} Mails nach Tab 2 geschoben. Verarbeite...", gr.update(selected=1)

            final_t2 = list(new_t2)
            for m in moved_this_session:
                final_t2.append(m)

            for i in range(len(new_t2), len(final_t2)):
                mail = final_t2[i]
                mail_path = Path(mail["path"])

                logger.info(f"Generiere Zusammenfassung für {mail['lastname']}...")
                mail["summary"] = controller.generate_short_summary(mail_path)
                mail["similarity_info"] = controller.get_similarity_info(mail_path, mail["lastname"])

                yield new_t1, list(final_t2), f"Verarbeitet: {mail['lastname']} ({i - len(new_t2) + 1}/{len(moved_this_session)})", gr.update(selected=1)

            yield new_t1, final_t2, "Verarbeitung abgeschlossen.", gr.update(selected=1)

        def relocate_remaining(t1_mails: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
            """Archiviert alle verbleibenden E-Mails in Tab 1."""
            if not t1_mails:
                return [], "Keine Mails zum Verschieben."

            changes = []
            for m in t1_mails:
                change = m.copy()
                change["new_class"] = m["class"]
                changes.append(change)

            try:
                errors = controller.relocate_emails(changes)
                if errors:
                    return t1_mails, "Fehler beim Verschieben: " + "; ".join(errors)
                return [], "Mails erfolgreich archiviert."
            except Exception as e:
                logger.error(f"Fehler beim Archivieren: {e}")
                return t1_mails, f"Fehler: {str(e)}"

    demo.launch(inbrowser=True)

def main() -> None:
    """Hauptfunktion zum Starten der Gradio GUI."""
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
        debug=args.debug,
        use_action_classifier=args.use_action_classifier
    )

    try:
        run_gradio_gui(controller, source_dir, method=args.method, mode=args.mode, age_months=args.age_months)
    except Exception as e:
        logger.error(f"Fehler beim Starten der Gradio GUI: {e}")

if __name__ == "__main__":
    main()
