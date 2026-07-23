"""Gradio-GUI für die Verwaltung von wöchentlichen Terminen."""
import os
import platform
import subprocess
import urllib.parse
from fastapi.responses import HTMLResponse
import re
import yaml
import pandas as pd
import gradio as gr
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from mcp_university.config import get_config
from email_classifier.scripts.sort_emails import extract_lastname, find_student_folder
from academic_parser.mail_parser import MailParser
from mcp_university.summarizer.engine import Summarizer
from mcp_university.summarizer.profiler import PersonProfiler

class Tools:
    """Lazy-loading Container für Tools um Startzeit zu optimieren."""
    _parser: Optional[MailParser] = None
    _summarizer: Optional[Summarizer] = None
    _profiler: Optional[PersonProfiler] = None
    _classifier: Optional[Any] = None

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

    @classmethod
    def classifier(cls) -> Optional[Any]:
        """Gibt eine geladene Instanz des EmailClassifiers zurück oder None.

        Returns:
            Optional[Any]: Eine Instanz des EmailClassifiers oder None.
        """
        if cls._classifier is None:
            try:
                from email_classifier.engine import EmailClassifier, resolve_model_path
                config = get_config()
                model_path = None
                for method in ["transformer", "xgboost", "randomforest"]:
                    for mode in ["tfidf", "combined", "embedding"]:
                        try_path = resolve_model_path(config.data_dir / "email_classifier.pkl", method, mode)
                        if try_path.exists():
                            model_path = try_path
                            break
                    if model_path:
                        break

                if not model_path:
                    model_path = resolve_model_path(config.data_dir / "email_classifier.pkl", "transformer", "tfidf")

                if model_path.exists():
                    import torch
                    try:
                        data = torch.load(model_path, map_location="cpu", weights_only=False)
                        method = data.get("method", "randomforest")
                        mode = data.get("mode", "combined")
                    except Exception:
                        method = "transformer"
                        mode = "tfidf"

                    clf = EmailClassifier(method=method, mode=mode)
                    clf.load(model_path)
                    cls._classifier = clf
                else:
                    import logging
                    logging.getLogger(__name__).warning(f"Klassifikator-Modell unter {model_path} nicht gefunden.")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Fehler beim Laden des EmailClassifiers: {e}")
        return cls._classifier


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

        # Zeige immer eine Woche ab heute (00:00 Uhr)
        start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        # check if we have ANY data for this week
        mask = (df["dt"] >= start_of_week) & (df["dt"] < end_of_week)
        if mask.any():
            df = df[mask]
        else:
            pass

    except Exception as e:
        print(f"Error parsing dates: {e}")

    # Termine absolut sortieren nach Datum/Uhrzeit
    if "dt" in df.columns:
        df = df.sort_values("dt")
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


def check_folder_contains_participant_emails(student_dir: Path, email: Optional[str], lastname: Optional[str]) -> bool:
    """Überprüft, ob der Ordner E-Mails des Teilnehmers enthält.

    Es wird nach .msg und .eml Dateien im Ordner gesucht. Falls vorhanden,
    wird geprüft, ob der Absender oder Empfänger dem Teilnehmer (E-Mail oder Nachname) entspricht.

    Args:
        student_dir (Path): Der Pfad zum Studentenordner.
        email (Optional[str]): Die E-Mail-Adresse des Teilnehmers.
        lastname (Optional[str]): Der Nachname des Teilnehmers.

    Returns:
        bool: True, wenn passende E-Mails gefunden wurden, sonst False.
    """
    if not student_dir or not student_dir.exists():
        return False

    email_files = list(student_dir.rglob("*.msg")) + list(student_dir.rglob("*.eml"))
    if not email_files:
        return False

    if not email and not lastname:
        return True

    academic_parser = Tools.mail_parser()
    for f in email_files:
        try:
            details = academic_parser.get_email_details(f)

            if email:
                email_lower = email.lower()
                from_email = details.get("from_email")
                if from_email and email_lower in from_email.lower():
                    return True
                for recipient in details.get("to", []):
                    rec_email = recipient.get("email")
                    if rec_email and email_lower in rec_email.lower():
                        return True
                for recipient in details.get("cc", []):
                    rec_email = recipient.get("email")
                    if rec_email and email_lower in rec_email.lower():
                        return True

            if lastname:
                lastname_lower = lastname.lower()
                from_name = details.get("from_name")
                if from_name and lastname_lower in from_name.lower():
                    return True
                for recipient in details.get("to", []):
                    rec_name = recipient.get("name")
                    if rec_name and lastname_lower in rec_name.lower():
                        return True
                for recipient in details.get("cc", []):
                    rec_name = recipient.get("name")
                    if rec_name and lastname_lower in rec_name.lower():
                        return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Fehler beim Überprüfen der E-Mail {f}: {e}")

    return False


def get_class_from_title(
    title: str,
    class_paths: Dict[str, str],
    email: Optional[str] = None,
    lastname: Optional[str] = None
) -> str:
    """Bestimmt die E-Mail-Klasse basierend auf dem Terminbetreff.

    Wird keine Übereinstimmung im Betreff gefunden, dann wird der Betreff
    an das Emailclassifier Modell übergeben, welches über die Klasse entscheidet.
    Wenn im vorhergesagten Klassenordner keine Mails von dem Teilnehmer des Termins
    gefunden werden, fällt das System auf die Standardklasse "Other" zurück.

    Args:
        title (str): Der Betreff des Termins.
        class_paths (Dict[str, str]): Die konfigurierten Pfade.
        email (Optional[str]): Die E-Mail-Adresse des Teilnehmers.
        lastname (Optional[str]): Der Nachname des Teilnehmers.

    Returns:
        str: Die gefundene Klasse oder 'Other'.
    """
    for class_name in class_paths.keys():
        if class_name.lower() in title.lower():
            return class_name

    # Keine direkte Übereinstimmung im Betreff -> Klassifikator verwenden
    clf = Tools.classifier()
    if clf:
        try:
            res = clf.predict_text(title)
            pred_cls = res.get("prediction")
            if pred_cls and pred_cls in class_paths:
                # Wir prüfen, ob im vorhergesagten Klassenordner Mails vom Teilnehmer existieren
                pred_base_path = Path(class_paths[pred_cls])
                pred_student_dir = find_student_folder(pred_base_path, lastname) if lastname else None

                if pred_student_dir and check_folder_contains_participant_emails(pred_student_dir, email, lastname):
                    return pred_cls
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Fehler bei der Klassifizierung des Betreffs: {e}")

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

    lastname = extract_lastname(participant_info)
    email = extract_email(participant_info)
    class_paths = get_class_paths()
    cls = get_class_from_title(title, class_paths, email, lastname)

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


@demo.app.get("/open-folder")
def open_folder_endpoint(path: str) -> HTMLResponse:
    """FastAPI endpoint to open a folder in the native file explorer.

    It decodes the path, checks its existence, and opens it on Windows
    using os.startfile, or open/xdg-open on macOS/Linux.

    Args:
        path (str): The URL-encoded absolute path of the folder to open.

    Returns:
        HTMLResponse: An HTML page indicating success or failure.
    """
    decoded_path = urllib.parse.unquote(path)

    if not decoded_path or not Path(decoded_path).exists():
        html_content = f"""
        <html>
        <head>
            <title>Fehler</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #fff0f0;
                    color: #a00;
                }}
                .card {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    display: inline-block;
                    max-width: 500px;
                    width: 100%;
                    border: 1px solid #fcc;
                }}
                button {{
                    background: #f44336;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h3>Ordner nicht gefunden!</h3>
                <p>Der Pfad existiert nicht oder ist ung&uuml;ltig.</p>
                <p><code>{decoded_path}</code></p>
                <button onclick="window.close()">Fenster schlie&szlig;en</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=404)

    try:
        if platform.system() == "Windows":
            os.startfile(decoded_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", decoded_path])
        else:
            subprocess.run(["xdg-open", decoded_path])

        html_content = f"""
        <html>
        <head>
            <title>Ordner ge&ouml;ffnet</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f4f4f9;
                    color: #333;
                }}
                .card {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    display: inline-block;
                    max-width: 500px;
                    width: 100%;
                }}
                h3 {{ color: #2e7d32; }}
                code {{
                    display: block;
                    background: #eee;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 15px 0;
                    word-break: break-all;
                }}
                button {{
                    background: #2196f3;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }}
            </style>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 2000);
            </script>
        </head>
        <body>
            <div class="card">
                <h3>Ordner erfolgreich ge&ouml;ffnet!</h3>
                <p>Der folgende Ordner wurde im Explorer ge&ouml;ffnet:</p>
                <code>{decoded_path}</code>
                <p><small>Dieses Fenster schlie&szlig;t sich in K&uuml;rze automatisch.</small></p>
                <button onclick="window.close()">Fenster schlie&szlig;en</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        html_content = f"""
        <html>
        <head>
            <title>Fehler</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #fff0f0;
                }}
            </style>
        </head>
        <body>
            <h3>Fehler beim &Ouml;ffnen des Ordners</h3>
            <p>{e}</p>
            <button onclick="window.close()">Fenster schlie&szlig;en</button>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)


if __name__ == "__main__":
    demo.launch(inbrowser=True)
