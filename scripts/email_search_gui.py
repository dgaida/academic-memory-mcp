"""Gradio-GUI für die schnelle Suche nach E-Mails."""

import os
import platform
import subprocess
import pandas as pd
import gradio as gr
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from mcp_university.utils.email_search import EmailSearchEngine
from mcp_university.parser.mail_parser import MailParser

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
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
        return f"Geöffnet: {filepath}"
    except Exception as e:
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
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder])
        elif platform.system() == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
        return f"Ordner geöffnet: {folder}"
    except Exception as e:
        return f"Fehler beim Öffnen des Ordners: {e}"

def search_emails(query: str) -> pd.DataFrame:
    """Führt die Suche aus und gibt ein DataFrame zurück.

    Args:
        query (str): Der Suchbegriff.

    Returns:
        pd.DataFrame: Die Suchergebnisse.
    """
    if not query:
        return pd.DataFrame(columns=["Datum", "Von", "Betreff", "Pfad"])
    results = GUITools.engine().search(query)
    if not results:
        return pd.DataFrame(columns=["Datum", "Von", "Betreff", "Pfad"])

    data = []
    for res in results:
        data.append([
            res["date"][:10], # Nur das Datum
            res["from_name"] or res["from"],
            res["subject"],
            res["path"]
        ])

    return pd.DataFrame(data, columns=["Datum", "Von", "Betreff", "Pfad"])

def get_suggestions(query: str) -> Dict[str, Any]:
    """Gibt Vorschläge für das Suchfeld zurück.

    Args:
        query (str): Der bisherige Suchbegriff.

    Returns:
        Dict[str, Any]: Gradio-Update für die Choices.
    """
    if not query or len(query) < 2:
        return gr.update(choices=[])
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
        print(error_msg)
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

            email_list = gr.DataFrame(
                headers=["Datum", "Von", "Betreff", "Pfad"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Gefundene E-Mails"
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
        outputs=[email_list]
    )

    email_list.select(
        fn=display_email,
        inputs=[email_list],
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
    demo.launch()
