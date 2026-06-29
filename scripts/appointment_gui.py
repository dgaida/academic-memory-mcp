"""Gradio-GUI für die Verwaltung von wöchentlichen Terminen."""
import os
import platform
import subprocess
import re
import yaml
import pandas as pd
import gradio as gr
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from mcp_university.config import get_config
from email_classifier.sort_emails import extract_lastname, find_student_folder
from mcp_university.parser.mail_parser import MailParser
from mcp_university.summarizer.engine import Summarizer
from mcp_university.summarizer.profiler import PersonProfiler

class Tools:
    """Lazy-loading Container für Tools um Startzeit zu optimieren."""
    _parser: Optional[MailParser] = None
    _summarizer: Optional[Summarizer] = None
    _profiler: Optional[PersonProfiler] = None

    @classmethod
    def mail_parser(cls) -> MailParser:
        """Gibt eine Instanz des MailParsers zurück.

        Returns:
            MailParser: Eine Instanz des MailParsers.
        """
        if cls._parser is None:
            cls._parser = MailParser()
        return cls._parser

    @classmethod
    def summarizer(cls) -> Summarizer:
        """Gibt eine Instanz des Summarizers zurück.

        Returns:
            Summarizer: Eine Instanz des Summarizers.
        """
        if cls._summarizer is None:
            cls._summarizer = Summarizer()
        return cls._summarizer

    @classmethod
    def profiler(cls) -> PersonProfiler:
        """Gibt eine Instanz des PersonProfilers zurück.

        Returns:
            PersonProfiler: Eine Instanz des PersonProfilers.
        """
        if cls._profiler is None:
            cls._profiler = PersonProfiler()
        return cls._profiler


def open_file(filepath: str) -> str:
    """Öffnet eine Datei mit der Standardanwendung des Betriebssystems.

    Args:
        filepath (str): Der Pfad zur Datei.

    Returns:
        str: Eine Statusmeldung.
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


def parse_appointments() -> pd.DataFrame:
    """Parst die Termine aus der appointments.md Datei.

    Returns:
        pd.DataFrame: Ein DataFrame mit den Terminen.
    """
    config = get_config()
    file_path = config.data_dir / "appointments.md"
    if not file_path.exists():
        return pd.DataFrame(columns=["Start", "Betreff", "Teilnehmer"])

    content = ""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if not content:
        # Fallback mit Replacement
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    lines = content.splitlines()
    data = []
    headers = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("Zeitraum:") or line.startswith("Generiert am:"):
            continue

        if "|" in line:
            if "---" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            # Remove empty first/last parts if pipe-wrapped
            if parts and not parts[0]:
                parts.pop(0)
            if parts and not parts[-1]:
                parts.pop()
        else:
            # Assume tab or whitespace separated
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if len(parts) < 2:
                parts = [p.strip() for re_split in [re.split(r'\s{2,}', line)] for p in re_split if p.strip()]

        if not parts:
            continue

        if not headers and ("Datum" in parts or "Start" in parts or "Thema" in parts):
            headers = parts
            continue

        if headers:
            data.append(parts)

    if not headers or not data:
        return pd.DataFrame(columns=["Start", "Betreff", "Teilnehmer"])

    df_raw = pd.DataFrame(data, columns=headers[:len(data[0])])

    # Map columns to standard format
    result_data = []
    for _, row in df_raw.iterrows():
        start = ""
        if "Start" in row:
            start = row["Start"]
        elif "Datum" in row:
            start = row["Datum"]
            if "Uhrzeit" in row:
                start += f" {row['Uhrzeit']}"

        betreff = ""
        if "Betreff" in row:
            betreff = row["Betreff"]
        elif "Thema" in row:
            betreff = row["Thema"]

        teilnehmer = row.get("Teilnehmer", "")

        result_data.append([start, betreff, teilnehmer])

    df = pd.DataFrame(result_data, columns=["Start", "Betreff", "Teilnehmer"])

    # Filter for this week
    try:
        df["dt"] = pd.to_datetime(df["Start"], errors='coerce')
        now = datetime.now()

        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        # check if we have ANY data for this week
        mask = (df["dt"] >= start_of_week) & (df["dt"] < end_of_week)
        if mask.any():
            df = df[mask]
        else:
            pass

    except Exception as e:
        print(f"Error parsing dates: {e}")

    if "dt" in df.columns:
        df = df.drop(columns=["dt"])
    return df


def get_class_paths() -> Dict[str, str]:
    """Gibt die konfigurierten Pfade für die E-Mail-Klassen zurück.

    Returns:
        Dict[str, str]: Ein Dictionary mit Klassen-Pfaden.
    """
    config = get_config()
    cp_path = config.config_dir / "classifier_paths.yaml"
    if not cp_path.exists():
        cp_path = config.config_dir / "classifier_paths.yaml.example"

    with open(cp_path, "r", encoding="utf-8", errors="replace") as f:
        cp_data = yaml.safe_load(f)
    return cp_data.get("class_paths", {})


def get_class_from_title(title: str, class_paths: Dict[str, str]) -> str:
    """Bestimmt die E-Mail-Klasse basierend auf dem Terminbetreff.

    Args:
        title (str): Der Betreff des Termins.
        class_paths (Dict[str, str]): Die konfigurierten Pfade.

    Returns:
        str: Die gefundene Klasse oder 'Other'.
    """
    for class_name in class_paths.keys():
        if class_name.lower() in title.lower():
            return class_name
    return "Other"


def extract_email(text: str) -> Optional[str]:
    """Extrahiert eine E-Mail-Adresse aus einem String.

    Args:
        text (str): Der zu durchsuchende Text.

    Returns:
        Optional[str]: Die gefundene E-Mail-Adresse oder None.
    """
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else None


def load_student_details(evt: gr.SelectData, df: pd.DataFrame) -> Tuple[str, str, Optional[str], str]:
    """Lädt Details zu einem Studenten basierend auf einem ausgewählten Termin.

    Args:
        evt (gr.SelectData): Das Selektions-Event aus der Gradio Tabelle.
        df (pd.DataFrame): Das DataFrame mit den Terminen.

    Returns:
        Tuple[str, str, Optional[str], str]: Zusammenfassung, Steckbrief, Explorer-Root, Pfad-String.
    """
    row_idx = evt.index[0]
    title = df.iloc[row_idx]["Betreff"]
    participant_info = df.iloc[row_idx]["Teilnehmer"]

    class_paths = get_class_paths()
    cls = get_class_from_title(title, class_paths)
    lastname = extract_lastname(participant_info)
    email = extract_email(participant_info)

    student_dir = None
    if cls in class_paths:
        base_path = Path(class_paths[cls])
        student_dir = find_student_folder(base_path, lastname)

    if not student_dir:
        for bp_str in class_paths.values():
            student_dir = find_student_folder(Path(bp_str), lastname)
            if student_dir:
                break

    if student_dir:
        summary_path = student_dir / ".emails_summary.md"
        # 1) Freshness check for .emails_summary.md
        email_files = list(student_dir.rglob("*.msg")) + list(student_dir.rglob("*.eml"))
        if email_files:
            latest_email_date = max(Tools.mail_parser().get_email_date(f) for f in email_files)

            summary_outdated = False
            if not summary_path.exists():
                summary_outdated = True
            else:
                summary_mtime = datetime.fromtimestamp(summary_path.stat().st_mtime)
                if latest_email_date > summary_mtime:
                    summary_outdated = True

            if summary_outdated:
                dated_emails = []
                for f in email_files:
                    try:
                        dated_emails.append((Tools.mail_parser().get_email_date(f), f))
                    except Exception:
                        dated_emails.append((datetime.min, f))
                dated_emails.sort(key=lambda x: x[0])

                conversation_content = ""
                for d, f in dated_emails:
                    parsed = Tools.mail_parser().parse(f)
                    if parsed:
                        conversation_content += f"\n--- EMAIL VOM {d} ---\n{parsed}\n"

                new_summary = Tools.summarizer().summarize_email_conversation(student_dir.name, conversation_content)
                if new_summary:
                    summary_path.write_text(new_summary, encoding="utf-8")

    summary = "### Ordner-Zusammenfassung\n\nKeine Zusammenfassung gefunden."
    if student_dir:
        summary_path = student_dir / ".emails_summary.md"
        if summary_path.exists():
            summary = f"### Ordner-Zusammenfassung\n\n{summary_path.read_text(encoding='utf-8', errors='replace')}"

    profile = "### Steckbrief\n\nKein Steckbrief gefunden."
    if email:
        # 2) Automatic Steckbrief generation/update
        profile_content = Tools.profiler().get_profile(email)
        if profile_content:
            profile = f"### Steckbrief\n\n{profile_content}"
        else:
            # Fallback to existing logic if profiler fails to produce content
            profile_path = Path("Steckbriefe") / f"{email}.md"
            if not profile_path.exists():
                profile_path = Path(r"D:\Steckbriefe") / f"{email}.md"

            if profile_path.exists():
                profile = f"### Steckbrief\n\n{profile_path.read_text(encoding='utf-8', errors='replace')}"

    explorer_root = str(student_dir) if student_dir and student_dir.exists() else None

    return summary, profile, explorer_root, str(student_dir) if student_dir else ""


def on_file_select(evt: gr.SelectData) -> Any:
    """Wird aufgerufen wenn eine Datei im Explorer ausgewählt wird.

    Args:
        evt (gr.SelectData): Das Selektions-Event.

    Returns:
        Any: Der Pfad zur Datei.
    """
    return evt.value


with gr.Blocks(title="Appointment Manager") as demo:
    gr.Markdown("# Wochen-Terminplaner & Student-Info")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Termine dieser Woche")
            appointments_df = gr.State(parse_appointments())
            table = gr.DataFrame(value=parse_appointments(), interactive=False)
            refresh_btn = gr.Button("Aktualisieren")

        with gr.Column(scale=2):
            summary_md = gr.Markdown("### Ordner-Zusammenfassung\n\nWähle einen Termin aus.")
            profile_md = gr.Markdown("### Steckbrief\n\nWähle einen Termin aus.")

        with gr.Column(scale=1):
            gr.Markdown("### Dateisystem")
            student_path_display = gr.Textbox(label="Studenten-Pfad", interactive=False)
            explorer = gr.FileExplorer(label="Dateien (Klick zum Öffnen)", file_count="single")
            open_status = gr.Textbox(label="Status", interactive=False)

    def update_table() -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Aktualisiert die Tabelle der Termine.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Die neuen Daten für die GUI.
        """
        new_df = parse_appointments()
        return new_df, new_df

    refresh_btn.click(update_table, outputs=[table, appointments_df])

    def handle_selection(evt: gr.SelectData, df: pd.DataFrame) -> Tuple[str, str, Any, str]:
        """Verarbeitet die Auswahl eines Termins.

        Args:
            evt: Selektions-Event.
            df: Aktuelles DataFrame.

        Returns:
            Gradio Updates für die UI.
        """
        summary, profile, folder_root, folder_str = load_student_details(evt, df)
        if folder_root:
            return summary, profile, gr.update(root_dir=folder_root, visible=True), folder_str
        else:
            return summary, profile, gr.update(visible=False), ""

    table.select(
        handle_selection,
        inputs=[appointments_df],
        outputs=[summary_md, profile_md, explorer, student_path_display]
    )

    def open_selected_file(evt: gr.SelectData, student_dir: str) -> str:
        """Öffnet die ausgewählte Datei.

        Args:
            evt: Selektions-Event.
            student_dir: Der Pfad zum Studenten-Ordner.

        Returns:
            Statusmeldung.
        """
        if not student_dir:
            return "Kein Studenten-Ordner ausgewählt."
        full_path = Path(student_dir) / evt.value[0] if isinstance(evt.value, list) else Path(student_dir) / evt.value
        return open_file(str(full_path))

    explorer.select(open_selected_file, inputs=[student_path_display], outputs=[open_status])

if __name__ == "__main__":
    demo.launch(inbrowser=True)
