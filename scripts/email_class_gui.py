"""Gradio-GUI für die E-Mail-Suche nach E-Mail-Klassen."""

import os
import platform
import subprocess
import logging
import pandas as pd
import gradio as gr
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from mcp_university.utils.email_search import EmailSearchEngine
from academic_parser.mail_parser import MailParser
from mcp_university.summarizer.profiler import PersonProfiler

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_class_gui")


class GUITools:
    """Lazy-loading Container für Tools."""
    _engine: Optional[EmailSearchEngine] = None
    _parser: Optional[MailParser] = None
    _profiler: Optional[PersonProfiler] = None

    @classmethod
    def engine(cls) -> EmailSearchEngine:
        """Gibt eine Instanz der SearchEngine zurück.

        Returns:
            EmailSearchEngine: Die Such-Engine.
        """
        if cls._engine is None:
            logger.info("Initialisiere EmailSearchEngine...")
            cls._engine = EmailSearchEngine()
            cls._engine.update_index()
        return cls._engine

    @classmethod
    def academic_parser(cls) -> MailParser:
        """Gibt eine Instanz des MailParsers zurück.

        Returns:
            MailParser: Der Mail-Parser.
        """
        if cls._parser is None:
            cls._parser = MailParser()
        return cls._parser

    @classmethod
    def profiler(cls) -> PersonProfiler:
        """Gibt eine Instanz des PersonProfilers zurück.

        Returns:
            PersonProfiler: Der Person-Profiler.
        """
        if cls._profiler is None:
            cls._profiler = PersonProfiler()
        return cls._profiler


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


def load_email_classes() -> List[str]:
    """Lädt alle verfügbaren E-Mail-Klassen für das Dropdown-Menü.

    Returns:
        List[str]: Liste der E-Mail-Klassen.
    """
    return GUITools.engine().get_email_classes()


def on_class_change(selected_class: str) -> Tuple[
    pd.DataFrame, str, Dict[str, Any], str, pd.DataFrame, pd.DataFrame, str, str, str
]:
    """Wird aufgerufen, wenn eine E-Mail-Klasse im Dropdown ausgewählt wird.

    Args:
        selected_class (str): Die ausgewählte E-Mail-Klasse.

    Returns:
        Tuple[pd.DataFrame, str, Dict[str, Any], str, pd.DataFrame, pd.DataFrame, str, str, str]:
        Aktualisierter Adressen-DataFrame, Steckbrief-Text, Button-Update, Steckbrief-Status,
        Inbox-DF, Sent-DF, E-Mail-Adresse State, E-Mail-Viewer HTML, Statusmeldung.
    """
    logger.info(f"E-Mail-Klasse ausgewählt: {selected_class}")
    empty_emails_df = pd.DataFrame(columns=["Datum", "Von", "Betreff", "Pfad"])
    empty_addr_df = pd.DataFrame(columns=["Name", "E-Mail-Adresse", "Anzahl E-Mails"])
    viewer_placeholder = "<div style='text-align: center; padding: 50px; color: gray;'>Wähle eine E-Mail aus der Liste aus.</div>"

    if not selected_class:
        return (
            empty_addr_df,
            "### Steckbrief\nWähle eine E-Mail-Klasse und eine E-Mail-Adresse aus.",
            gr.update(visible=False),
            "",
            empty_emails_df,
            empty_emails_df,
            "",
            viewer_placeholder,
            "Keine E-Mail-Klasse ausgewählt."
        )

    addresses = GUITools.engine().get_addresses_for_class(selected_class)
    addr_data = []
    for item in addresses:
        addr_data.append([
            item.get("name") or "(Kein Name)",
            item.get("email") or "",
            item.get("count", 0)
        ])

    addr_df = pd.DataFrame(addr_data, columns=["Name", "E-Mail-Adresse", "Anzahl E-Mails"])
    status_msg = f"Klasse '{selected_class}': {len(addr_data)} E-Mail-Adresse(n) gefunden."
    logger.info(status_msg)

    return (
        addr_df,
        "### Steckbrief\nWähle eine E-Mail-Adresse aus der Liste oben.",
        gr.update(visible=False),
        "",
        empty_emails_df,
        empty_emails_df,
        "",
        viewer_placeholder,
        status_msg
    )


def check_steckbrief_status(email_address: str) -> Tuple[str, Dict[str, Any], str]:
    """Prüft, ob ein Steckbrief vorhanden ist und gibt Inhalt/Button-Status zurück.

    Args:
        email_address (str): Die E-Mail-Adresse.

    Returns:
        Tuple[str, Dict[str, Any], str]: Markdown-Inhalt, Button-Update, Statusmeldung.
    """
    if not email_address:
        return "### Steckbrief\nWähle eine E-Mail-Adresse aus.", gr.update(visible=False), ""

    profiler = GUITools.profiler()
    profile_file = profiler.storage_path / f"{email_address}.md"

    if profile_file.exists() and profile_file.stat().st_size > 0:
        try:
            content = profile_file.read_text(encoding="utf-8")
            logger.info(f"Steckbrief für {email_address} geladen.")
            return content, gr.update(visible=False), f"Steckbrief für {email_address} geladen."
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Steckbriefs {profile_file}: {e}")

    logger.info(f"Kein Steckbrief für {email_address} vorhanden.")
    no_profile_md = f"### Kein Steckbrief vorhanden\nFür **{email_address}** wurde noch kein Steckbrief erstellt."
    return no_profile_md, gr.update(visible=True, value="Steckbrief generieren"), f"Kein Steckbrief für {email_address} vorhanden."


def on_address_select(evt: gr.SelectData, df: pd.DataFrame, selected_class: str) -> Tuple[
    str, Dict[str, Any], str, pd.DataFrame, pd.DataFrame, str, str, str
]:
    """Wird aufgerufen, wenn eine E-Mail-Adresse in der Liste angeklickt wird.

    Args:
        evt (gr.SelectData): Das Selektions-Event.
        df (pd.DataFrame): Das aktuelle Adressen-DataFrame.
        selected_class (str): Die aktuell ausgewählte E-Mail-Klasse.

    Returns:
        Tuple[str, Dict[str, Any], str, pd.DataFrame, pd.DataFrame, str, str, str]:
        Steckbrief-Markdown, Button-Update, Steckbrief-Status, Inbox-DF, Sent-DF,
        E-Mail-Adresse State, Viewer-HTML, Statusmeldung.
    """
    row_idx = evt.index[0]
    email_address = str(df.iloc[row_idx]["E-Mail-Adresse"])
    logger.info(f"E-Mail-Adresse ausgewählt: {email_address} (Klasse: {selected_class})")

    profile_md, btn_update, profile_status = check_steckbrief_status(email_address)

    inbox_list, sent_list = GUITools.engine().get_emails_for_class_and_address(selected_class, email_address)

    cols = ["Datum", "Von", "Betreff", "Pfad"]
    inbox_rows = []
    for item in inbox_list:
        inbox_rows.append([
            item.get("date", "")[:10],
            item.get("from_name") or item.get("from", ""),
            item.get("subject", ""),
            item.get("path", "")
        ])

    sent_rows = []
    for item in sent_list:
        sent_rows.append([
            item.get("date", "")[:10],
            item.get("from_name") or item.get("from", ""),
            item.get("subject", ""),
            item.get("path", "")
        ])

    inbox_df = pd.DataFrame(inbox_rows, columns=cols)
    sent_df = pd.DataFrame(sent_rows, columns=cols)

    viewer_placeholder = "<div style='text-align: center; padding: 50px; color: gray;'>Wähle eine E-Mail aus der Liste aus.</div>"
    status_msg = f"Adresse '{email_address}': {len(inbox_rows)} Inbox, {len(sent_rows)} SentItems E-Mail(s)."

    return (
        profile_md,
        btn_update,
        profile_status,
        inbox_df,
        sent_df,
        email_address,
        viewer_placeholder,
        status_msg
    )


def generate_steckbrief_action(email_address: str) -> Tuple[str, Dict[str, Any], str]:
    """Generiert einen Steckbrief für die angegebene E-Mail-Adresse.

    Args:
        email_address (str): Die E-Mail-Adresse.

    Returns:
        Tuple[str, Dict[str, Any], str]: Steckbrief-Content, Button-Update, Statusmeldung.
    """
    if not email_address:
        return "Keine E-Mail-Adresse gewählt.", gr.update(visible=False), "Fehler: Keine E-Mail-Adresse."

    logger.info(f"Generiere Steckbrief für: {email_address}")
    try:
        profile_content = GUITools.profiler().generate_profile(email_address, force_update=True)
        if profile_content:
            logger.info(f"Steckbrief für {email_address} erfolgreich generiert.")
            return (
                profile_content,
                gr.update(visible=False),
                f"Steckbrief für {email_address} erfolgreich generiert."
            )
        else:
            return (
                f"### Fehler\nFür **{email_address}** konnte kein Steckbrief generiert werden (keine E-Mails/Daten vorhanden).",
                gr.update(visible=True, value="Erneut versuchen"),
                "Steckbrief-Generierung fehlgeschlagen."
            )
    except Exception as e:
        logger.error(f"Fehler bei Steckbrief-Generierung für {email_address}: {e}")
        return (
            f"### Fehler bei Steckbrief-Generierung\n\n```\n{e}\n```",
            gr.update(visible=True, value="Erneut versuchen"),
            f"Fehler: {e}"
        )


def display_email(evt: gr.SelectData, df: pd.DataFrame) -> Tuple[str, str, str]:
    """Zeigt die ausgewählte E-Mail im HTML-Viewer an.

    Args:
        evt (gr.SelectData): Das Selektions-Event.
        df (pd.DataFrame): Das aktuelle E-Mail-DataFrame.

    Returns:
        Tuple[str, str, str]: HTML-Inhalt, Pfad, Statusmeldung.
    """
    row_idx = evt.index[0]
    path = str(df.iloc[row_idx]["Pfad"])
    logger.info(f"E-Mail ausgewählt: {path}")

    try:
        details = GUITools.academic_parser().get_email_details(Path(path))
        body = details.get("body", "Kein Inhalt")

        to_list = details.get('to', [])
        formatted_to = []
        for t in to_list:
            if isinstance(t, dict):
                formatted_to.append(f"{t.get('name', '')} <{t.get('email', '')}>".strip())
            else:
                formatted_to.append(str(t))

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


custom_css = """
.gradio-dataframe .table-wrap,
.gradio-dataframe .scroll-container {
    overflow-y: scroll !important;
}
.gradio-dataframe .table-wrap::-webkit-scrollbar,
.gradio-dataframe .scroll-container::-webkit-scrollbar {
    -webkit-appearance: none;
    width: 8px !important;
    height: 8px !important;
}
.gradio-dataframe .table-wrap::-webkit-scrollbar-thumb,
.gradio-dataframe .scroll-container::-webkit-scrollbar-thumb {
    background-color: rgba(128, 128, 128, 0.5) !important;
    border-radius: 4px !important;
}
.gradio-dataframe .table-wrap::-webkit-scrollbar-track,
.gradio-dataframe .scroll-container::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05) !important;
}
"""

with gr.Blocks(title="E-Mail-Suche nach Emailklassen", css=custom_css) as demo:
    gr.Markdown("# 📁 E-Mail-Suche nach Emailklassen")
    gr.Markdown(
        "Finde E-Mail-Adressen und E-Mails zu einer bestimmten E-Mail-Klasse, "
        "wenn du dich nicht mehr an die E-Mail-Adresse oder den Namen erinnerst."
    )

    selected_class_state = gr.State("")
    selected_email_address_state = gr.State("")
    selected_path_state = gr.State("")

    with gr.Row():
        with gr.Column(scale=1):
            class_dropdown = gr.Dropdown(
                label="E-Mail-Klasse auswählen",
                choices=[],
                value=None,
                interactive=True
            )

            gr.Markdown("### 👥 Ausgetauschte E-Mail-Adressen")
            address_list = gr.DataFrame(
                headers=["Name", "E-Mail-Adresse", "Anzahl E-Mails"],
                datatype=["str", "str", "number"],
                interactive=False,
                label="Ausgetauschte E-Mail-Adressen",
                max_height=300
            )

        with gr.Column(scale=1):
            gr.Markdown("### 👤 Steckbrief")
            steckbrief_viewer = gr.Markdown(
                value="### Steckbrief\nWähle eine E-Mail-Klasse und eine E-Mail-Adresse aus."
            )
            generate_steckbrief_btn = gr.Button(
                "Steckbrief generieren",
                variant="primary",
                visible=False
            )
            steckbrief_status = gr.Textbox(
                label="Steckbrief-Status",
                interactive=False,
                visible=True
            )

    gr.Markdown("---")
    gr.Markdown("## ✉️ E-Mails zur ausgewählten Adresse und Klasse")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📥 Posteingang (Inbox)")
            inbox_list = gr.DataFrame(
                headers=["Datum", "Von", "Betreff", "Pfad"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Posteingang",
                max_height=300
            )

            gr.Markdown("### 📤 Gesendete Elemente (SentItems)")
            sent_list = gr.DataFrame(
                headers=["Datum", "Von", "Betreff", "Pfad"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Gesendete Mails",
                max_height=300
            )

        with gr.Column(scale=1):
            gr.Markdown("### 📄 E-Mail-Vorschau")
            email_viewer = gr.HTML(
                value="<div style='text-align: center; padding: 50px; color: gray;'>Wähle eine E-Mail aus der Liste aus.</div>",
                label="Email Viewer"
            )

            with gr.Row():
                open_outlook_btn = gr.Button("Öffnen in Outlook")
                open_explorer_btn = gr.Button("Öffnen in Explorer")

            status_output = gr.Textbox(label="Status", interactive=False)

    # Initiales Laden der E-Mail-Klassen beim Anzeigen der GUI
    demo.load(
        fn=lambda: gr.update(choices=load_email_classes()),
        outputs=[class_dropdown]
    )

    # Events
    class_dropdown.change(
        fn=on_class_change,
        inputs=[class_dropdown],
        outputs=[
            address_list,
            steckbrief_viewer,
            generate_steckbrief_btn,
            steckbrief_status,
            inbox_list,
            sent_list,
            selected_email_address_state,
            email_viewer,
            status_output
        ]
    )

    address_list.select(
        fn=on_address_select,
        inputs=[address_list, class_dropdown],
        outputs=[
            steckbrief_viewer,
            generate_steckbrief_btn,
            steckbrief_status,
            inbox_list,
            sent_list,
            selected_email_address_state,
            email_viewer,
            status_output
        ]
    )

    generate_steckbrief_btn.click(
        fn=generate_steckbrief_action,
        inputs=[selected_email_address_state],
        outputs=[
            steckbrief_viewer,
            generate_steckbrief_btn,
            steckbrief_status
        ]
    )

    inbox_list.select(
        fn=display_email,
        inputs=[inbox_list],
        outputs=[email_viewer, selected_path_state, status_output]
    )

    sent_list.select(
        fn=display_email,
        inputs=[sent_list],
        outputs=[email_viewer, selected_path_state, status_output]
    )

    open_outlook_btn.click(
        fn=open_in_outlook,
        inputs=[selected_path_state],
        outputs=[status_output]
    )

    open_explorer_btn.click(
        fn=open_in_explorer,
        inputs=[selected_path_state],
        outputs=[status_output]
    )

if __name__ == "__main__":
    logger.info("Starte E-Mail-Klassen-GUI...")
    GUITools.engine()
    demo.launch(inbrowser=True)
