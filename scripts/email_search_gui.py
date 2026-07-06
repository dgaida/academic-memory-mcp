"""Gradio-GUI für die schnelle Suche nach E-Mails."""

import os
import platform
import subprocess
import logging
import pandas as pd
import gradio as gr
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from mcp_university.utils.email_search import EmailSearchEngine
from mcp_university.parser.mail_parser import MailParser

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_search_gui")

class GUITools:
    """Lazy-loading Container für Tools."""
    _engine: Optional[EmailSearchEngine] = None
    _parser: Optional[MailParser] = None

    @classmethod
    def engine(cls) -> EmailSearchEngine:
        """Gibt eine Instanz der SearchEngine zurück.

        Returns:
            EmailSearchEngine: Die Such-Engine.
        """
        if cls._engine is None:
            logger.info("Initialisiere EmailSearchEngine...")
            cls._engine = EmailSearchEngine()
            # Beim ersten Start Index aktualisieren
            cls._engine.update_index()
        return cls._engine

    @classmethod
    def parser(cls) -> MailParser:
        """Gibt eine Instanz des MailParsers zurück.

        Returns:
            MailParser: Der Mail-Parser.
        """
        if cls._parser is None:
            cls._parser = MailParser()
        return cls._parser

def open_in_outlook(filepath: str) -> str:
    """Öffnet die Datei in Outlook (oder Standardanwendung).

    Args:
        filepath (str): Pfad zur Datei.

    Returns:
        str: Statusmeldung.
    """
    if not filepath or not Path(filepath).exists():
        return f"Datei nicht gefunden: {filepath}"

    filepath = str(Path(filepath).absolute())
    logger.info(f"Öffne Datei in Outlook: {filepath}")
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
        return f"Geöffnet: {filepath}"
    except Exception as e:
        logger.error(f"Fehler beim Öffnen der Datei: {e}")
        return f"Fehler beim Öffnen: {e}"

def open_in_explorer(filepath: str) -> str:
    """Öffnet den Ordner im Explorer.

    Args:
        filepath (str): Pfad zur Datei.

    Returns:
        str: Statusmeldung.
    """
    if not filepath or not Path(filepath).exists():
        return f"Datei nicht gefunden: {filepath}"

    folder = str(Path(filepath).parent.absolute())
    logger.info(f"Öffne Ordner im Explorer: {folder}")
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder])
        elif platform.system() == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
        return f"Ordner geöffnet: {folder}"
    except Exception as e:
        logger.error(f"Fehler beim Öffnen des Ordners: {e}")
        return f"Fehler beim Öffnen des Ordners: {e}"

def search_emails(query: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Führt die Suche aus und gibt DataFrames für Inbox und SentItems zurück.

    Args:
        query (str): Der Suchbegriff.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Inbox-Ergebnisse, SentItems-Ergebnisse.
    """
    cols = ["Datum", "Von", "Betreff", "Pfad"]
    empty_df = pd.DataFrame(columns=cols)

    if not query:
        return empty_df, empty_df

    logger.info(f"Suche nach: {query}")
    results = GUITools.engine().search(query)
    if not results:
        logger.info("Keine Ergebnisse gefunden.")
        return empty_df, empty_df

    inbox_data = []
    sent_data = []

    for res in results:
        row = [
            res["date"][:10], # Nur das Datum
            res["from_name"] or res["from"],
            res["subject"],
            res["path"]
        ]
        if res.get("folder") == "SentItems":
            sent_data.append(row)
        else:
            inbox_data.append(row)

    logger.info(f"Suche abgeschlossen. Inbox: {len(inbox_data)}, SentItems: {len(sent_data)}")
    return pd.DataFrame(inbox_data, columns=cols), pd.DataFrame(sent_data, columns=cols)

def get_suggestions(query: str) -> Dict[str, Any]:
    """Gibt Vorschläge für das Suchfeld zurück.

    Args:
        query (str): Der bisherige Suchbegriff.

    Returns:
        Dict[str, Any]: Gradio-Update für die Choices.
    """
    if not query or len(query) < 2:
        return gr.update(choices=[])

    logger.info(f"Hole Vorschläge für: {query}")
    suggestions = GUITools.engine().get_suggestions(query)
    return gr.update(choices=suggestions)

def display_email(evt: gr.SelectData, df: pd.DataFrame) -> Tuple[str, str, str]:
    """Zeigt die ausgewählte E-Mail an.

    Args:
        evt (gr.SelectData): Das Selektions-Event.
        df (pd.DataFrame): Das aktuelle DataFrame.

    Returns:
        Tuple[str, str, str]: HTML-Inhalt, Pfad, Statusmeldung.
    """
    row_idx = evt.index[0]
    path = df.iloc[row_idx]["Pfad"]
    logger.info(f"E-Mail ausgewählt: {path}")

    try:
        details = GUITools.parser().get_email_details(Path(path))
        body = details.get("body", "Kein Inhalt")

        # Sicherstellen, dass 'to' eine Liste von Strings ist
        to_list = details.get('to', [])
        formatted_to = []
        for t in to_list:
            if isinstance(t, dict):
                formatted_to.append(f"{t.get('name', '')} <{t.get('email', '')}>".strip())
            else:
                formatted_to.append(str(t))

        # Einfaches HTML für die Anzeige
        html_content = f"""
        <div style='font-family: sans-serif;'>
            <p><b>Von:</b> {details.get('from_name')} &lt;{details.get('from_email')}&gt;</p>
            <p><b>An:</b> {', '.join(formatted_to)}</p>
            <p><b>Datum:</b> {details.get('date')}</p>
            <p><b>Betreff:</b> {details.get('subject')}</p>
            <hr>
            <pre style='white-space: pre-wrap; word-wrap: break-word;'>{body}</pre>
        </div>
        """
        return html_content, path, f"Datei ausgewählt: {path}"
    except Exception as e:
        import traceback
        error_msg = f"Fehler beim Laden der E-Mail: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return f"<p>Fehler beim Laden der E-Mail: {e}</p>", "", error_msg

with gr.Blocks(title="Email Search Quick") as demo:
    gr.Markdown("# 📧 Email Schnellsuche")

    with gr.Row():
        with gr.Column(scale=1):
            search_input = gr.Dropdown(
                label="Suche (Name, E-Mail, Betreff...)",
                allow_custom_value=True,
                choices=[],
                filterable=True
            )

            search_btn = gr.Button("Suchen", variant="primary")

            gr.Markdown("### 📥 Posteingang (Inbox)")
            inbox_list = gr.DataFrame(
                headers=["Datum", "Von", "Betreff", "Pfad"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Posteingang", max_height=400
            )

            gr.Markdown("### 📤 Gesendete Elemente (SentItems)")
            sent_list = gr.DataFrame(
                headers=["Datum", "Von", "Betreff", "Pfad"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Gesendete Mails", max_height=400
            )

        with gr.Column(scale=1):
            email_viewer = gr.HTML(
                value="<div style='text-align: center; padding: 50px; color: gray;'>Wähle eine E-Mail aus der Liste aus.</div>",
                label="Email Viewer"
            )

            with gr.Row():
                open_outlook_btn = gr.Button("Öffnen in Outlook")
                open_explorer_btn = gr.Button("Öffnen in Explorer")

            status_output = gr.Textbox(label="Status", interactive=False)
            selected_path = gr.State("")

    # Events
    search_input.change(
        fn=get_suggestions,
        inputs=[search_input],
        outputs=[search_input]
    )

    search_btn.click(
        fn=search_emails,
        inputs=[search_input],
        outputs=[inbox_list, sent_list]
    )

    inbox_list.select(
        fn=display_email,
        inputs=[inbox_list],
        outputs=[email_viewer, selected_path, status_output]
    )

    sent_list.select(
        fn=display_email,
        inputs=[sent_list],
        outputs=[email_viewer, selected_path, status_output]
    )

    open_outlook_btn.click(
        fn=open_in_outlook,
        inputs=[selected_path],
        outputs=[status_output]
    )

    open_explorer_btn.click(
        fn=open_in_explorer,
        inputs=[selected_path],
        outputs=[status_output]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
