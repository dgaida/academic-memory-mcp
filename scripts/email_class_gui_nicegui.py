"""Modernes NiceGUI-basiertes Interface für E-Mail-Klassen, Suche & Wochen-Termine.

Bietet schnelle Tabellen (Quasar/AG-Grid), echte Split-Pane-Ansichten,
sofortige Anzeige vorhandener Steckbriefe mit nicht-blockierenden
Hintergrund-Tasks zur Aktualisierung sowie optionalen nativen Windows-Desktop-Modus.
"""

import os
import platform
import subprocess
import logging
import argparse
import re
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from nicegui import ui, run

from mcp_university.config import get_config
from mcp_university.utils.email_search import EmailSearchEngine
from academic_parser.mail_parser import MailParser
from mcp_university.summarizer.profiler import PersonProfiler

# Robuste Importe für Sortier- und Ordnerlogik
try:
    from email_classifier.scripts.sort_emails import extract_lastname, find_student_folder
except ImportError:
    def extract_lastname(text: str) -> str:
        """Fallback zur Extraktion des Nachnamens aus Namen oder E-Mail-Adresse.

        Args:
            text (str): Namens- oder Adress-String.

        Returns:
            str: Extrahierter Nachname oder 'Unknown'.
        """
        if not text:
            return "Unknown"
        match = re.search(r"[\w\.-]+@[\w\.-]+", text)
        if match:
            local = match.group(0).split("@")[0]
            if "." in local:
                return local.split(".")[-1].capitalize()
        words = text.split()
        return words[-1].capitalize() if words else "Unknown"

    def find_student_folder(base_directory: Path, lastname: str) -> Optional[Path]:
        """Fallback zum Auffinden des Studentenordners.

        Args:
            base_directory (Path): Basisordner der Klasse.
            lastname (str): Nachname des Studenten.

        Returns:
            Optional[Path]: Pfad zum Ordner oder None.
        """
        if not base_directory or not base_directory.exists() or not lastname or lastname == "Unknown":
            return None
        lastname_lower = lastname.lower()
        for folder in base_directory.rglob("*"):
            if folder.is_dir() and lastname_lower in folder.name.lower():
                return folder
        return None

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_class_gui_nicegui")


class GUITools:
    """Lazy-loading Container für Backend-Services."""
    _engine: Optional[EmailSearchEngine] = None
    _parser: Optional[MailParser] = None
    _profiler: Optional[PersonProfiler] = None
    _summarizer: Optional[Any] = None
    _classifier: Optional[Any] = None

    @classmethod
    def engine(cls) -> EmailSearchEngine:
        """Gibt eine Instanz der SearchEngine zurück.

        Returns:
            EmailSearchEngine: Die Such-Engine.
        """
        if cls._engine is None:
            logger.info("Initialisiere EmailSearchEngine...")
            cls._engine = EmailSearchEngine()
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

    @classmethod
    def profiler(cls) -> PersonProfiler:
        """Gibt eine Instanz des PersonProfilers zurück.

        Returns:
            PersonProfiler: Der Person-Profiler.
        """
        if cls._profiler is None:
            cls._profiler = PersonProfiler()
        return cls._profiler

    @classmethod
    def summarizer(cls) -> Optional[Any]:
        """Gibt eine Instanz des Summarizers zurück.

        Returns:
            Optional[Any]: Der Summarizer oder None bei Fehler.
        """
        if cls._summarizer is None:
            try:
                from mcp_university.summarizer.engine import Summarizer
                cls._summarizer = Summarizer()
            except Exception as exc:
                logger.warning(f"Summarizer konnte nicht geladen werden: {exc}")
        return cls._summarizer

    @classmethod
    def classifier(cls) -> Optional[Any]:
        """Gibt eine Instanz des EmailClassifiers zurück.

        Returns:
            Optional[Any]: Der Klassifikator oder None.
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
                if model_path and model_path.exists():
                    clf = EmailClassifier(method="transformer", mode="tfidf")
                    clf.load(model_path)
                    cls._classifier = clf
            except Exception as exc:
                logger.debug(f"Klassifikator-Laden übersprungen: {exc}")
        return cls._classifier


def safe_notify(message: str, type: str = 'info', position: str = 'bottom-right') -> None:
    """Zeigt eine Benachrichtigung an, falls ein aktiver NiceGUI-Client-Kontext vorhanden ist.

    Args:
        message (str): Die anzuzeigende Nachricht.
        type (str): Der Benachrichtigungstyp ('info', 'warning', 'positive', 'negative').
        position (str): Die Position auf dem Bildschirm.
    """
    try:
        safe_notify(message, type=type, position=position)
    except Exception:
        pass


def open_in_outlook(filepath: str) -> str:
    """Öffnet die angegebene E-Mail in Outlook bzw. der Standardanwendung.

    Args:
        filepath (str): Absoluter Pfad zur E-Mail-Datei.

    Returns:
        str: Statusmeldung über das Ergebnis.
    """
    if not filepath or not Path(filepath).exists():
        msg = f"Datei nicht gefunden: {filepath}"
        logger.warning(msg)
        return msg

    target_path = str(Path(filepath).absolute())
    logger.info(f"Öffne Datei in Outlook: {target_path}")
    try:
        if platform.system() == "Windows":
            os.startfile(target_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", target_path], check=False)
        else:
            subprocess.run(["xdg-open", target_path], check=False)
        return f"In Outlook geöffnet: {Path(target_path).name}"
    except Exception as exc:
        err = f"Fehler beim Öffnen: {exc}"
        logger.error(err)
        return err


def open_in_explorer(filepath: str) -> str:
    """Öffnet den Ordner der Datei bzw. das Verzeichnis im Explorer.

    Args:
        filepath (str): Absoluter Pfad zur Datei oder zum Ordner.

    Returns:
        str: Statusmeldung über das Ergebnis.
    """
    if not filepath or not Path(filepath).exists():
        msg = f"Pfad nicht gefunden: {filepath}"
        logger.warning(msg)
        return msg

    target = Path(filepath).absolute()
    folder = str(target if target.is_dir() else target.parent)
    logger.info(f"Öffne Ordner im Explorer: {folder}")
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", folder], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
        return f"Ordner geöffnet: {folder}"
    except Exception as exc:
        err = f"Fehler beim Öffnen des Ordners: {exc}"
        logger.error(err)
        return err


def open_file(filepath: str) -> str:
    """Öffnet eine Datei mit der Standardanwendung des Betriebssystems.

    Args:
        filepath (str): Der Pfad zur Datei.

    Returns:
        str: Eine Statusmeldung über das Ergebnis.
    """
    if not filepath or not Path(filepath).exists():
        msg = f"Datei nicht gefunden: {filepath}"
        logger.warning(msg)
        return msg

    target_path = str(Path(filepath).absolute())
    logger.info(f"Öffne Datei: {target_path}")
    try:
        if platform.system() == "Windows":
            os.startfile(target_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", target_path], check=False)
        else:
            subprocess.run(["xdg-open", target_path], check=False)
        return f"Geöffnet: {Path(target_path).name}"
    except Exception as exc:
        err = f"Fehler beim Öffnen: {exc}"
        logger.error(err)
        return err


def extract_email(text: str) -> Optional[str]:
    """Extrahiert die erste E-Mail-Adresse aus einem String.

    Args:
        text (str): Zu durchsuchender Text.

    Returns:
        Optional[str]: Extrahierte E-Mail-Adresse in Kleinbuchstaben oder None.
    """
    if not text:
        return None
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0).lower() if match else None


def get_class_paths() -> Dict[str, str]:
    """Gibt die konfigurierten Pfade für die E-Mail-Klassen zurück.

    Returns:
        Dict[str, str]: Dictionary mit Klassen-Pfaden.
    """
    try:
        config = get_config()
        cp_path = config.config_dir / "classifier_paths.yaml"
        if not cp_path.exists():
            cp_path = config.config_dir / "classifier_paths.yaml.example"

        if cp_path.exists():
            with open(cp_path, "r", encoding="utf-8", errors="replace") as f:
                cp_data = yaml.safe_load(f)
            return cp_data.get("class_paths", {})
    except Exception as exc:
        logger.warning(f"Fehler beim Laden von classifier_paths.yaml: {exc}")
    return {}


def get_class_from_title(
    title: str,
    class_paths: Dict[str, str],
    email: Optional[str] = None,
    lastname: Optional[str] = None
) -> str:
    """Bestimmt die E-Mail-Klasse basierend auf dem Terminbetreff.

    Args:
        title (str): Der Betreff des Termins.
        class_paths (Dict[str, str]): Die konfigurierten Pfade.
        email (Optional[str]): Die E-Mail-Adresse des Teilnehmers.
        lastname (Optional[str]): Der Nachname des Teilnehmers.

    Returns:
        str: Die bestimmte E-Mail-Klasse oder 'Other'.
    """
    if not title:
        return "Other"

    for class_name in class_paths.keys():
        if class_name.lower() in title.lower():
            return class_name

    clf = GUITools.classifier()
    if clf:
        try:
            res = clf.predict_text(title)
            pred_cls = res.get("prediction")
            if pred_cls and pred_cls in class_paths:
                return pred_cls
        except Exception as exc:
            logger.debug(f"Klassifizierung des Betreffs übersprungen: {exc}")

    return "Other"


def parse_appointments(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Parst die Termine aus der appointments.md Datei.

    Filtert die Termine primär für die laufende Woche (ab heute 00:00 Uhr für 7 Tage).
    Gibt alle Termine sortiert zurück, falls für diese Woche keine explizit gefunden werden.

    Args:
        file_path (Optional[Path]): Optionaler Pfad zur appointments.md.

    Returns:
        List[Dict[str, Any]]: Liste der Termine mit 'start', 'subject', 'participant'.
    """
    if file_path is None:
        try:
            config = get_config()
            file_path = config.data_dir / "appointments.md"
        except Exception as exc:
            logger.warning(f"Konnte Konfigurationspfad nicht laden: {exc}")
            file_path = Path("data/appointments.md")

    if not file_path.exists():
        logger.warning(f"Termin-Datei existiert nicht: {file_path}")
        return []

    content = ""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if not content:
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
            if parts and not parts[0]:
                parts.pop(0)
            if parts and not parts[-1]:
                parts.pop()
        else:
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if len(parts) < 2:
                parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]

        if not parts:
            continue

        if not headers and any(h in parts for h in ["Datum", "Start", "Thema", "Betreff"]):
            headers = parts
            continue

        if headers:
            data.append(parts)

    if not headers or not data:
        return []

    result_rows = []
    for row_parts in data:
        row_dict = dict(zip(headers[:len(row_parts)], row_parts))
        start = ""
        if "Start" in row_dict:
            start = row_dict["Start"]
        elif "Datum" in row_dict:
            start = row_dict["Datum"]
            if "Uhrzeit" in row_dict:
                start += f" {row_dict['Uhrzeit']}"

        betreff = ""
        if "Betreff" in row_dict:
            betreff = row_dict["Betreff"]
        elif "Thema" in row_dict:
            betreff = row_dict["Thema"]

        teilnehmer = row_dict.get("Teilnehmer", "")

        result_rows.append({
            "start": start,
            "subject": betreff,
            "participant": teilnehmer
        })

    # Sortierung und Wochen-Filterung
    parsed_entries = []
    for r in result_rows:
        dt = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
            try:
                dt = datetime.strptime(r["start"].strip(), fmt)
                break
            except Exception:
                pass
        parsed_entries.append((dt, r))

    now = datetime.now()
    start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)

    matching_this_week = [p for p in parsed_entries if p[0] and start_of_week <= p[0] < end_of_week]
    if matching_this_week:
        sorted_week = sorted(matching_this_week, key=lambda x: x[0])
        return [r for _, r in sorted_week]

    sorted_all = sorted(parsed_entries, key=lambda x: (x[0] is None, x[0] or datetime.min))
    return [r for _, r in sorted_all]


class EmailClassApp:
    """Haupt-Applikationsklasse für das erweiterte NiceGUI E-Mail- & Termin-Interface."""

    def __init__(self) -> None:
        """Initialisiert die Anwendungszustände und Datenstrukturen."""
        self.selected_class: str = ""
        self.selected_address: str = ""
        self.selected_email_path: str = ""

        # UI-Komponenten Referenzen
        self.class_select: Optional[ui.select] = None
        self.status_label: Optional[ui.label] = None

        # Tab 1 Komponenten (Letzte Mails)
        self.recent_inbox_table: Optional[ui.table] = None
        self.recent_sent_table: Optional[ui.table] = None
        self.tab1_viewer_title: Optional[ui.label] = None
        self.tab1_viewer_meta: Optional[ui.markdown] = None
        self.tab1_viewer_body: Optional[ui.markdown] = None
        self.tab1_btn_outlook: Optional[ui.button] = None
        self.tab1_btn_explorer: Optional[ui.button] = None

        # Tab 2 Komponenten (Nach Adresse & Steckbrief)
        self.addresses_table: Optional[ui.table] = None
        self.tab_person_inbox: Optional[ui.tab] = None
        self.tab_person_sent: Optional[ui.tab] = None
        self.person_inbox_table: Optional[ui.table] = None
        self.person_sent_table: Optional[ui.table] = None
        self.steckbrief_container: Optional[ui.card] = None
        self.steckbrief_markdown: Optional[ui.markdown] = None
        self.steckbrief_btn: Optional[ui.button] = None
        self.steckbrief_spinner: Optional[ui.spinner] = None
        self.tab2_viewer_meta: Optional[ui.markdown] = None
        self.tab2_viewer_body: Optional[ui.markdown] = None
        self.tab2_btn_outlook: Optional[ui.button] = None
        self.tab2_btn_explorer: Optional[ui.button] = None

        # Tab 3 Komponenten (E-Mail Schnellsuche)
        self.search_input: Optional[ui.input] = None
        self.search_suggestions_select: Optional[ui.select] = None
        self.search_inbox_table: Optional[ui.table] = None
        self.search_sent_table: Optional[ui.table] = None
        self.tab3_inbox_label: Optional[ui.label] = None
        self.tab3_sent_label: Optional[ui.label] = None
        self.tab3_viewer_title: Optional[ui.label] = None
        self.tab3_viewer_meta: Optional[ui.markdown] = None
        self.tab3_viewer_body: Optional[ui.markdown] = None
        self.tab3_btn_outlook: Optional[ui.button] = None
        self.tab3_btn_explorer: Optional[ui.button] = None

        # Tab 4 Komponenten (Wochen-Termine & Steckbrief)
        self.appointments_table: Optional[ui.table] = None
        self.refresh_appointments_btn: Optional[ui.button] = None
        self.selected_appointment: Optional[Dict[str, Any]] = None
        self.app_participant_email: str = ""
        self.app_student_dir: Optional[Path] = None
        self.app_steckbrief_markdown: Optional[ui.markdown] = None
        self.app_steckbrief_spinner: Optional[ui.spinner] = None
        self.app_steckbrief_status: Optional[ui.label] = None
        self.app_steckbrief_refresh_btn: Optional[ui.button] = None
        self.app_summary_markdown: Optional[ui.markdown] = None
        self.app_summary_refresh_btn: Optional[ui.button] = None
        self.app_student_folder_label: Optional[ui.label] = None
        self.app_btn_explorer: Optional[ui.button] = None
        self.app_files_table: Optional[ui.table] = None
        self.app_file_status: Optional[ui.label] = None

    def build_ui(self) -> None:
        """Erstellt die vollständige Benutzeroberfläche in NiceGUI."""
        ui.colors(primary='#1976D2', secondary='#26A69A', accent='#9C27B0')

        with ui.header().classes('items-center justify-between bg-slate-800 text-white shadow-md px-6 py-2'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('mail', size='2rem').classes('text-blue-400')
                with ui.column().classes('gap-0'):
                    ui.label('Academic Memory — E-Mail & Termin-Zentrale').classes('text-lg font-bold')
                    ui.label('Klassen, Schnellsuche, Termine & automatische Steckbriefe').classes('text-xs text-slate-300')

            with ui.row().classes('items-center gap-4'):
                email_classes = GUITools.engine().get_email_classes()
                self.class_select = ui.select(
                    options=email_classes,
                    label='E-Mail-Klasse wählen',
                    with_input=True,
                    on_change=self.on_class_selected
                ).classes('w-72 bg-white rounded').props('dense outlined clearable')

                ui.dark_mode().bind_value(ui.switch('Dark', value=False).classes('text-white text-xs'))

        # Tabs Navigation mit 4 Reitern
        with ui.tabs().classes('w-full border-b bg-slate-50') as tabs:
            tab_recent = ui.tab('🕒 Letzte Mails der Klasse', icon='schedule')
            tab_address = ui.tab('👥 Nach E-Mail-Adresse & Steckbrief', icon='people')
            tab_search = ui.tab('🔍 E-Mail Schnellsuche', icon='search')
            tab_appointment = ui.tab('📅 Wochen-Termine & Steckbrief', icon='event')

        with ui.tab_panels(tabs, value=tab_recent).classes('w-full h-full p-4'):
            # TAB 1: Letzte Mails
            with ui.tab_panel(tab_recent):
                self._build_tab_recent()

            # TAB 2: Nach Adresse & Steckbrief
            with ui.tab_panel(tab_address):
                self._build_tab_address()

            # TAB 3: Schnellsuche
            with ui.tab_panel(tab_search):
                self._build_tab_search()

            # TAB 4: Termine & Steckbrief
            with ui.tab_panel(tab_appointment):
                self._build_tab_appointment()

        # Footer mit Statuszeile
        with ui.footer().classes('bg-slate-100 text-slate-700 text-xs px-4 py-1.5 border-t justify-between items-center'):
            self.status_label = ui.label('Bereit. Wähle oben eine Klasse oder navigiere durch die Tabs.')
            ui.label('MCP University • Offline-First').classes('text-slate-400 font-mono')

        # Termine für Tab 4 initial asynchron laden
        ui.timer(0.2, self.load_appointments, once=True)

    def _build_tab_recent(self) -> None:
        """Baut den Inhalt von Tab 1 (Letzte Mails der Klasse) mit Splitter auf."""
        with ui.splitter(value=50).classes('w-full h-[calc(100vh-170px)]') as splitter:
            with splitter.before:
                with ui.column().classes('w-full p-2 gap-4 h-full overflow-y-auto'):
                    ui.label('📥 Posteingang (Inbox) — Letzte 10').classes('font-bold text-sm text-slate-700')
                    self.recent_inbox_table = ui.table(
                        columns=[
                            {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                            {'name': 'from', 'label': 'Von', 'field': 'from', 'sortable': True, 'align': 'left'},
                            {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                        ],
                        rows=[],
                        row_key='path',
                        pagination={'rowsPerPage': 5}
                    ).classes('w-full cursor-pointer')
                    self.recent_inbox_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=1))

                    ui.label('📤 Gesendete Elemente (SentItems) — Letzte 10').classes('font-bold text-sm text-slate-700')
                    self.recent_sent_table = ui.table(
                        columns=[
                            {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                            {'name': 'from', 'label': 'An/Von', 'field': 'from', 'sortable': True, 'align': 'left'},
                            {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                        ],
                        rows=[],
                        row_key='path',
                        pagination={'rowsPerPage': 5}
                    ).classes('w-full cursor-pointer')
                    self.recent_sent_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=1))

            with splitter.after:
                with ui.column().classes('w-full p-4 h-full overflow-y-auto border-l'):
                    with ui.row().classes('w-full items-center justify-between pb-2 border-b'):
                        self.tab1_viewer_title = ui.label('E-Mail-Vorschau').classes('text-base font-bold text-slate-800')
                        with ui.row().classes('gap-2'):
                            self.tab1_btn_outlook = ui.button(
                                'In Outlook öffnen',
                                icon='open_in_new',
                                on_click=lambda: self.trigger_open_outlook(1)
                            ).props('dense outline color=primary').classes('text-xs')
                            self.tab1_btn_outlook.set_visibility(False)

                            self.tab1_btn_explorer = ui.button(
                                'Im Explorer anzeigen',
                                icon='folder_open',
                                on_click=lambda: self.trigger_open_explorer(1)
                            ).props('dense outline color=secondary').classes('text-xs')
                            self.tab1_btn_explorer.set_visibility(False)

                    self.tab1_viewer_meta = ui.markdown('Wähle links eine E-Mail aus, um Details anzuzeigen.').classes('text-xs text-slate-600')
                    with ui.card().classes('w-full flex-grow p-3 bg-white border border-slate-200 overflow-y-auto'):
                        self.tab1_viewer_body = ui.markdown('').classes('text-sm font-sans')

    def _build_tab_address(self) -> None:
        """Baut den Inhalt von Tab 2 (Nach Adresse & Steckbrief) auf."""
        with ui.splitter(value=45).classes('w-full h-[calc(100vh-170px)]') as splitter:
            with splitter.before:
                with ui.column().classes('w-full p-2 gap-4 h-full overflow-y-auto'):
                    ui.label('👥 Kommunikationspartner dieser Klasse').classes('font-bold text-sm text-slate-700')
                    self.addresses_table = ui.table(
                        columns=[
                            {'name': 'name', 'label': 'Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                            {'name': 'email', 'label': 'E-Mail-Adresse', 'field': 'email', 'sortable': True, 'align': 'left'},
                            {'name': 'count', 'label': 'Mails', 'field': 'count', 'sortable': True, 'align': 'right'},
                        ],
                        rows=[],
                        row_key='email',
                        pagination={'rowsPerPage': 7}
                    ).classes('w-full cursor-pointer')
                    self.addresses_table.on('rowClick', lambda e: self.on_address_selected(e.args[1]))

                    ui.label('✉️ E-Mails der ausgewählten Person').classes('font-bold text-sm text-slate-700')
                    with ui.tabs().classes('w-full') as mail_tabs:
                        self.tab_person_inbox = ui.tab('person_inbox', label='📥 Posteingang', icon='inbox')
                        self.tab_person_sent = ui.tab('person_sent', label='📤 Gesendet', icon='send')

                    with ui.tab_panels(mail_tabs, value=self.tab_person_inbox).classes('w-full p-0'):
                        with ui.tab_panel(self.tab_person_inbox):
                            self.person_inbox_table = ui.table(
                                columns=[
                                    {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                                    {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                                ],
                                rows=[],
                                row_key='path',
                                pagination={'rowsPerPage': 5}
                            ).classes('w-full cursor-pointer')
                            self.person_inbox_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=2))

                        with ui.tab_panel(self.tab_person_sent):
                            self.person_sent_table = ui.table(
                                columns=[
                                    {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                                    {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                                ],
                                rows=[],
                                row_key='path',
                                pagination={'rowsPerPage': 5}
                            ).classes('w-full cursor-pointer')
                            self.person_sent_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=2))

            with splitter.after:
                with ui.column().classes('w-full p-4 h-full overflow-y-auto border-l gap-4'):
                    # Steckbrief-Bereich
                    with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 shadow-sm'):
                        with ui.row().classes('w-full items-center justify-between pb-1'):
                            ui.label('👤 Steckbrief').classes('text-base font-bold text-slate-800')
                            self.steckbrief_spinner = ui.spinner(size='sm').classes('hidden')
                            self.steckbrief_btn = ui.button(
                                'Steckbrief generieren',
                                icon='psychology',
                                on_click=self.generate_steckbrief
                            ).props('dense color=primary').classes('text-xs hidden')

                        self.steckbrief_markdown = ui.markdown(
                            'Wähle links eine Person aus der Adressliste aus.'
                        ).classes('text-sm text-slate-700')

                    # E-Mail-Vorschau der Person
                    with ui.column().classes('w-full flex-grow'):
                        with ui.row().classes('w-full items-center justify-between pb-1 border-b'):
                            ui.label('📄 E-Mail-Vorschau').classes('font-bold text-sm text-slate-800')
                            with ui.row().classes('gap-2'):
                                self.tab2_btn_outlook = ui.button(
                                    'In Outlook',
                                    icon='open_in_new',
                                    on_click=lambda: self.trigger_open_outlook(2)
                                ).props('dense outline color=primary').classes('text-xs')
                                self.tab2_btn_outlook.set_visibility(False)

                                self.tab2_btn_explorer = ui.button(
                                    'Explorer',
                                    icon='folder_open',
                                    on_click=lambda: self.trigger_open_explorer(2)
                                ).props('dense outline color=secondary').classes('text-xs')
                                self.tab2_btn_explorer.set_visibility(False)

                        self.tab2_viewer_meta = ui.markdown('').classes('text-xs text-slate-600')
                        with ui.card().classes('w-full p-3 bg-white border border-slate-200 flex-grow overflow-y-auto'):
                            self.tab2_viewer_body = ui.markdown('').classes('text-sm font-sans')

    def _build_tab_search(self) -> None:
        """Baut den Inhalt von Tab 3 (E-Mail Schnellsuche) mit Splitter auf."""
        with ui.splitter(value=50).classes('w-full h-[calc(100vh-170px)]') as splitter:
            with splitter.before:
                with ui.column().classes('w-full p-2 gap-3 h-full overflow-y-auto'):
                    ui.label('🔍 E-Mail Volltext- & Schnellsuche').classes('font-bold text-sm text-slate-700')

                    with ui.row().classes('w-full items-center gap-2'):
                        self.search_input = ui.input(
                            label='Suche (Name, E-Mail, Betreff...)',
                            placeholder='z. B. Mustermann, Bachelor, Prüfungsordnung...'
                        ).props('dense outlined clearable').classes('flex-grow')
                        self.search_input.on('keydown.enter', self.perform_search)
                        self.search_input.on('update:model-value', self.on_search_input_change)

                        ui.button(
                            'Suchen',
                            icon='search',
                            on_click=self.perform_search
                        ).props('dense color=primary').classes('text-xs px-4')

                    self.search_suggestions_select = ui.select(
                        options=[],
                        label='💡 Suchvorschläge / Autovervollständigung (Klick zur Übernahme)',
                        with_input=True,
                        on_change=self.on_suggestion_selected
                    ).props('dense outlined clearable').classes('w-full text-xs')

                    self.tab3_inbox_label = ui.label('📥 Posteingang (Inbox)').classes('font-bold text-sm text-slate-700 mt-2')
                    self.search_inbox_table = ui.table(
                        columns=[
                            {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                            {'name': 'from', 'label': 'Von', 'field': 'from', 'sortable': True, 'align': 'left'},
                            {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                        ],
                        rows=[],
                        row_key='path',
                        pagination={'rowsPerPage': 5}
                    ).classes('w-full cursor-pointer')
                    self.search_inbox_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=3))

                    self.tab3_sent_label = ui.label('📤 Gesendete Elemente (SentItems)').classes('font-bold text-sm text-slate-700')
                    self.search_sent_table = ui.table(
                        columns=[
                            {'name': 'date', 'label': 'Datum', 'field': 'date', 'sortable': True, 'align': 'left'},
                            {'name': 'from', 'label': 'An/Von', 'field': 'from', 'sortable': True, 'align': 'left'},
                            {'name': 'subject', 'label': 'Betreff', 'field': 'subject', 'sortable': True, 'align': 'left'},
                        ],
                        rows=[],
                        row_key='path',
                        pagination={'rowsPerPage': 5}
                    ).classes('w-full cursor-pointer')
                    self.search_sent_table.on('rowClick', lambda e: self.display_email_details(e.args[1], tab=3))

            with splitter.after:
                with ui.column().classes('w-full p-4 h-full overflow-y-auto border-l'):
                    with ui.row().classes('w-full items-center justify-between pb-2 border-b'):
                        self.tab3_viewer_title = ui.label('E-Mail-Vorschau').classes('text-base font-bold text-slate-800')
                        with ui.row().classes('gap-2'):
                            self.tab3_btn_outlook = ui.button(
                                'In Outlook öffnen',
                                icon='open_in_new',
                                on_click=lambda: self.trigger_open_outlook(3)
                            ).props('dense outline color=primary').classes('text-xs')
                            self.tab3_btn_outlook.set_visibility(False)

                            self.tab3_btn_explorer = ui.button(
                                'Im Explorer anzeigen',
                                icon='folder_open',
                                on_click=lambda: self.trigger_open_explorer(3)
                            ).props('dense outline color=secondary').classes('text-xs')
                            self.tab3_btn_explorer.set_visibility(False)

                    self.tab3_viewer_meta = ui.markdown('Führe eine Suche aus und wähle links eine E-Mail an.').classes('text-xs text-slate-600')
                    with ui.card().classes('w-full flex-grow p-3 bg-white border border-slate-200 overflow-y-auto'):
                        self.tab3_viewer_body = ui.markdown('').classes('text-sm font-sans')

    def _build_tab_appointment(self) -> None:
        """Baut den Inhalt von Tab 4 (Wochen-Termine & Steckbrief) mit Splitter auf."""
        with ui.splitter(value=48).classes('w-full h-[calc(100vh-170px)]') as splitter:
            with splitter.before:
                with ui.column().classes('w-full p-2 gap-3 h-full overflow-y-auto'):
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label('📅 Termine dieser Woche (appointments.md)').classes('font-bold text-sm text-slate-700')
                        self.refresh_appointments_btn = ui.button(
                            'Termine aktualisieren',
                            icon='refresh',
                            on_click=self.load_appointments
                        ).props('dense outline color=primary').classes('text-xs')

                    self.appointments_table = ui.table(
                        columns=[
                            {'name': 'start', 'label': 'Start / Datum', 'field': 'start', 'sortable': True, 'align': 'left'},
                            {'name': 'subject', 'label': 'Betreff / Thema', 'field': 'subject', 'sortable': True, 'align': 'left'},
                            {'name': 'participant', 'label': 'Teilnehmer', 'field': 'participant', 'sortable': True, 'align': 'left'},
                        ],
                        rows=[],
                        row_key='start',
                        pagination={'rowsPerPage': 6}
                    ).classes('w-full cursor-pointer')
                    self.appointments_table.on('rowClick', lambda e: self.on_appointment_selected(e.args[1]))

                    # Verzeichnis & Dateien des Teilnehmers
                    with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 mt-2'):
                        with ui.row().classes('w-full items-center justify-between pb-1'):
                            ui.label('📁 Zugehöriger Studentenordner & Dateien').classes('font-bold text-xs text-slate-700')
                            self.app_btn_explorer = ui.button(
                                'Im Explorer öffnen',
                                icon='folder_open',
                                on_click=self.trigger_open_student_folder
                            ).props('dense outline color=secondary').classes('text-xs hidden')

                        self.app_student_folder_label = ui.label('Kein Termin ausgewählt.').classes('text-xs text-slate-500 truncate')

                        self.app_files_table = ui.table(
                            columns=[
                                {'name': 'name', 'label': 'Dateiname', 'field': 'name', 'sortable': True, 'align': 'left'},
                                {'name': 'size', 'label': 'Größe', 'field': 'size', 'sortable': True, 'align': 'right'},
                                {'name': 'mtime', 'label': 'Datum', 'field': 'mtime', 'sortable': True, 'align': 'left'},
                            ],
                            rows=[],
                            row_key='path',
                            pagination={'rowsPerPage': 5}
                        ).classes('w-full cursor-pointer text-xs mt-1')
                        self.app_files_table.on('rowClick', lambda e: self.on_student_file_clicked(e.args[1]))

                        self.app_file_status = ui.label('Klicke auf eine Datei, um sie zu öffnen.').classes('text-xs text-slate-400')

            with splitter.after:
                with ui.column().classes('w-full p-4 h-full overflow-y-auto border-l gap-4'):
                    # 1. Steckbrief des Gesprächspartners (Sofortanzeige + Hintergrund-Aktualisierung)
                    with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 shadow-sm'):
                        with ui.row().classes('w-full items-center justify-between pb-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label('👤 Steckbrief des Gesprächspartners').classes('text-base font-bold text-slate-800')
                                self.app_steckbrief_spinner = ui.spinner(size='sm').classes('hidden')
                            with ui.row().classes('items-center gap-2'):
                                self.app_steckbrief_refresh_btn = ui.button(
                                    'Steckbrief aktualisieren',
                                    icon='sync',
                                    on_click=self.trigger_manual_steckbrief_update
                                ).props('dense outline color=primary').classes('text-xs hidden')

                        self.app_steckbrief_status = ui.label('').classes('text-xs text-slate-500 mb-2')
                        self.app_steckbrief_markdown = ui.markdown(
                            'Wähle links einen Termin aus, um den Steckbrief anzuzeigen.'
                        ).classes('text-sm text-slate-700')

                    # 2. Ordner-Zusammenfassung (.emails_summary.md)
                    with ui.card().classes('w-full p-4 bg-white border border-slate-200 shadow-sm flex-grow overflow-y-auto'):
                        with ui.row().classes('w-full items-center justify-between pb-1 border-b'):
                            ui.label('📋 Ordner-Zusammenfassung (.emails_summary.md)').classes('font-bold text-sm text-slate-800')
                            self.app_summary_refresh_btn = ui.button(
                                'Zusammenfassung neu erstellen',
                                icon='auto_awesome',
                                on_click=self.trigger_summary_update
                            ).props('dense outline color=primary').classes('text-xs hidden')

                        self.app_summary_markdown = ui.markdown(
                            'Wähle links einen Termin aus.'
                        ).classes('text-sm text-slate-700 mt-2')

    async def on_class_selected(self, event: Any) -> None:
        """Reagiert auf die Auswahl einer E-Mail-Klasse und befüllt Tabellen nicht-blockierend.

        Args:
            event (Any): Event-Objekt der Select-Komponente.
        """
        selected_val = event.value if hasattr(event, 'value') else event
        self.selected_class = selected_val or ""

        if not self.selected_class:
            self._clear_all_tables()
            if self.status_label:
                self.status_label.set_text("Keine E-Mail-Klasse ausgewählt.")
            return

        if self.status_label:
            self.status_label.set_text(f"Lade Daten für E-Mail-Klasse '{self.selected_class}'...")

        # 1. Tab 1: Letzte 10 Mails
        recent_inbox, recent_sent = await run.io_bound(
            GUITools.engine().get_recent_emails_for_class,
            self.selected_class,
            10
        )

        if self.recent_inbox_table:
            self.recent_inbox_table.rows = [
                {
                    'date': str(m.get('date', ''))[:10],
                    'from': m.get('from_name') or m.get('from', ''),
                    'subject': m.get('subject', '(Kein Betreff)'),
                    'path': m.get('path', '')
                }
                for m in recent_inbox
            ]
            self.recent_inbox_table.update()

        if self.recent_sent_table:
            self.recent_sent_table.rows = [
                {
                    'date': str(m.get('date', ''))[:10],
                    'from': m.get('from_name') or m.get('from', ''),
                    'subject': m.get('subject', '(Kein Betreff)'),
                    'path': m.get('path', '')
                }
                for m in recent_sent
            ]
            self.recent_sent_table.update()

        # 2. Tab 2: Adressliste der Klasse
        addresses = await run.io_bound(
            GUITools.engine().get_addresses_for_class,
            self.selected_class
        )

        if self.addresses_table:
            self.addresses_table.rows = [
                {
                    'name': a.get('name') or '(Unbekannt)',
                    'email': a.get('email', ''),
                    'count': a.get('count', 0)
                }
                for a in addresses
            ]
            self.addresses_table.update()

        # Tab 2 Person-Daten initial leeren, bis eine Person angeklickt wird
        self.selected_address = ""
        if self.person_inbox_table:
            self.person_inbox_table.rows = []
            self.person_inbox_table.update()
        if self.person_sent_table:
            self.person_sent_table.rows = []
            self.person_sent_table.update()
        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = '📥 Posteingang'
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = '📤 Gesendet'
            self.tab_person_sent.update()
        if self.steckbrief_markdown:
            self.steckbrief_markdown.set_content(
                "Wähle oben eine Person aus der Adressliste aus."
            )
        if self.steckbrief_btn:
            self.steckbrief_btn.set_visibility(False)
        if self.tab2_viewer_meta:
            self.tab2_viewer_meta.set_content("")
        if self.tab2_viewer_body:
            self.tab2_viewer_body.set_content("")
        if self.tab2_btn_outlook:
            self.tab2_btn_outlook.set_visibility(False)
        if self.tab2_btn_explorer:
            self.tab2_btn_explorer.set_visibility(False)

        status_msg = (
            f"Klasse '{self.selected_class}': {len(addresses)} Personen, "
            f"{len(recent_inbox)} Inbox-Mails, {len(recent_sent)} Sent-Mails geladen."
        )
        if self.status_label:
            self.status_label.set_text(status_msg)
        safe_notify(status_msg, type='info', position='bottom-right')

    async def on_address_selected(self, row_data: Dict[str, Any]) -> None:
        """Wird aufgerufen, wenn eine Person in der Adressliste angeklickt wird.

        Args:
            row_data (Dict[str, Any]): Zeilendaten der ausgewählten Person.
        """
        email_addr = row_data.get('email', '')
        self.selected_address = email_addr

        if not email_addr:
            return

        if self.status_label:
            self.status_label.set_text(f"Lade Details & E-Mails für: {email_addr}...")

        # 1. Steckbrief prüfen
        profiler = GUITools.profiler()
        profile_file = profiler.storage_path / f"{email_addr}.md"
        if not profile_file.exists():
            profile_file = Path("Steckbriefe") / f"{email_addr}.md"

        if profile_file.exists() and profile_file.stat().st_size > 0:
            try:
                content = profile_file.read_text(encoding="utf-8", errors="replace")
                if self.steckbrief_markdown:
                    self.steckbrief_markdown.set_content(content)
                if self.steckbrief_btn:
                    self.steckbrief_btn.set_visibility(False)
            except Exception as e:
                if self.steckbrief_markdown:
                    self.steckbrief_markdown.set_content(f"Fehler beim Laden des Steckbriefs: {e}")
                if self.steckbrief_btn:
                    self.steckbrief_btn.set_visibility(True)
        else:
            if self.steckbrief_markdown:
                self.steckbrief_markdown.set_content(
                    f"### Kein Steckbrief vorhanden\nFür **{email_addr}** existiert noch kein Steckbrief."
                )
            if self.steckbrief_btn:
                self.steckbrief_btn.set_text("Steckbrief generieren")
                self.steckbrief_btn.set_visibility(True)

        # 2. Mails dieser Person laden
        inbox_mails, sent_mails = await run.io_bound(
            GUITools.engine().get_emails_for_class_and_address,
            self.selected_class,
            email_addr
        )

        if self.person_inbox_table:
            self.person_inbox_table.rows = [
                {
                    'date': str(m.get('date', ''))[:10],
                    'subject': m.get('subject', '(Kein Betreff)'),
                    'path': m.get('path', '')
                }
                for m in inbox_mails
            ]
            self.person_inbox_table.update()

        if self.person_sent_table:
            self.person_sent_table.rows = [
                {
                    'date': str(m.get('date', ''))[:10],
                    'subject': m.get('subject', '(Kein Betreff)'),
                    'path': m.get('path', '')
                }
                for m in sent_mails
            ]
            self.person_sent_table.update()

        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = f"📥 Posteingang ({len(inbox_mails)})"
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = f"📤 Gesendet ({len(sent_mails)})"
            self.tab_person_sent.update()

        if self.status_label:
            self.status_label.set_text(
                f"Person '{email_addr}': {len(inbox_mails)} Inbox- und {len(sent_mails)} Sent-Mails."
            )

    async def generate_steckbrief(self) -> None:
        """Erzeugt im Hintergrund einen Steckbrief für die in Tab 2 gewählte Person."""
        if not self.selected_address:
            safe_notify("Keine Person ausgewählt!", type='warning')
            return

        if self.steckbrief_spinner:
            self.steckbrief_spinner.classes(remove='hidden')
        if self.steckbrief_btn:
            self.steckbrief_btn.disable()
        if self.status_label:
            self.status_label.set_text(f"Generiere Steckbrief für {self.selected_address} mit LLM...")

        try:
            profile_content = await run.io_bound(
                GUITools.profiler().generate_profile,
                self.selected_address,
                True
            )
            if profile_content:
                if self.steckbrief_markdown:
                    self.steckbrief_markdown.set_content(profile_content)
                if self.steckbrief_btn:
                    self.steckbrief_btn.set_visibility(False)
                safe_notify(f"Steckbrief für {self.selected_address} erfolgreich erstellt!", type='positive')
            else:
                if self.steckbrief_markdown:
                    self.steckbrief_markdown.set_content(
                        f"Fehler: Für **{self.selected_address}** konnte kein Steckbrief erzeugt werden."
                    )
                if self.steckbrief_btn:
                    self.steckbrief_btn.set_text("Erneut versuchen")
                    self.steckbrief_btn.enable()
        except Exception as exc:
            logger.error(f"Fehler bei Steckbrief-Generierung: {exc}")
            if self.steckbrief_markdown:
                self.steckbrief_markdown.set_content(f"Fehler: {exc}")
            if self.steckbrief_btn:
                self.steckbrief_btn.enable()
        finally:
            if self.steckbrief_spinner:
                self.steckbrief_spinner.classes(add='hidden')
            if self.status_label:
                self.status_label.set_text("Bereit.")

    # -------------------------------------------------------------
    # TAB 3 METHODEN: E-Mail Schnellsuche
    # -------------------------------------------------------------
    async def on_search_input_change(self, event: Any) -> None:
        """Aktualisiert dynamisch die Suchvorschläge beim Tippen.

        Args:
            event (Any): Event oder String des Suchbegriffs.
        """
        val = event.value if hasattr(event, 'value') else event
        query = (val or "").strip()
        if len(query) >= 2:
            suggestions = await run.io_bound(GUITools.engine().get_suggestions, query)
            if self.search_suggestions_select:
                self.search_suggestions_select.options = list(suggestions)[:20]
                self.search_suggestions_select.update()

    async def on_suggestion_selected(self, event: Any) -> None:
        """Übernimmt den ausgewählten Vorschlag in das Suchfeld und startet die Suche.

        Args:
            event (Any): Event der Select-Komponente.
        """
        val = event.value if hasattr(event, 'value') else event
        if val and self.search_input:
            self.search_input.value = str(val)
            await self.perform_search()

    async def perform_search(self) -> None:
        """Führt die E-Mail-Suche asynchron über die EmailSearchEngine aus."""
        query = (self.search_input.value if self.search_input else "").strip()
        if not query:
            safe_notify("Bitte einen Suchbegriff eingeben.", type='warning')
            return

        if self.status_label:
            self.status_label.set_text(f"Suche nach '{query}'...")

        results = await run.io_bound(GUITools.engine().search, query)

        inbox_rows = []
        sent_rows = []
        for res in results:
            row = {
                'date': str(res.get('date', ''))[:10],
                'from': res.get('from_name') or res.get('from', ''),
                'subject': res.get('subject', '(Kein Betreff)'),
                'path': res.get('path', '')
            }
            if res.get('folder') == 'SentItems':
                sent_rows.append(row)
            else:
                inbox_rows.append(row)

        if self.search_inbox_table:
            self.search_inbox_table.rows = inbox_rows
            self.search_inbox_table.update()
        if self.search_sent_table:
            self.search_sent_table.rows = sent_rows
            self.search_sent_table.update()

        if self.tab3_inbox_label:
            self.tab3_inbox_label.set_text(f"📥 Posteingang (Inbox) — {len(inbox_rows)} Treffer")
        if self.tab3_sent_label:
            self.tab3_sent_label.set_text(f"📤 Gesendete Elemente (SentItems) — {len(sent_rows)} Treffer")

        msg = f"Suche nach '{query}': {len(inbox_rows)} Inbox- und {len(sent_rows)} Sent-Mails gefunden."
        if self.status_label:
            self.status_label.set_text(msg)
        safe_notify(msg, type='info', position='bottom-right')

    # -------------------------------------------------------------
    # TAB 4 METHODEN: Wochen-Termine & Sofort-Steckbrief
    # -------------------------------------------------------------
    async def load_appointments(self) -> None:
        """Lädt die Termine aus appointments.md und befüllt die Tabelle."""
        if self.status_label:
            self.status_label.set_text("Lade Wochen-Termine aus appointments.md...")
        appointments = await run.io_bound(parse_appointments)
        if self.appointments_table:
            self.appointments_table.rows = appointments
            self.appointments_table.update()
        msg = f"{len(appointments)} Termine geladen."
        if self.status_label:
            self.status_label.set_text(msg)
        safe_notify(msg, type='info', position='bottom-right')

    async def on_appointment_selected(self, row_data: Dict[str, Any]) -> None:
        """Wird aufgerufen, wenn ein Termin angeklickt wird.

        Zeigt vorhandene Steckbriefe und Ordner-Zusammenfassungen SOFORT an,
        ohne auf das LLM zu warten, und startet erst danach die
        asynchrone Hintergrund-Aktualisierung.

        Args:
            row_data (Dict[str, Any]): Die Zeilendaten des ausgewählten Termins.
        """
        self.selected_appointment = row_data
        subject = row_data.get('subject', '')
        participant = row_data.get('participant', '')

        email = extract_email(participant)
        lastname = extract_lastname(participant)
        self.app_participant_email = email or ""

        if self.status_label:
            self.status_label.set_text(f"Termin ausgewählt: {subject} ({participant})")

        # 1. SOFORTIGE ANZEIGE DES VORHANDENEN STECKBRIEFS (ohne Wartezeit)
        existing_profile_content: Optional[str] = None
        if email:
            profiler = GUITools.profiler()
            candidate_paths = [
                profiler.storage_path / f"{email}.md",
                Path("Steckbriefe") / f"{email}.md",
                Path(r"D:\Steckbriefe") / f"{email}.md"
            ]
            for candidate in candidate_paths:
                if candidate.exists() and candidate.stat().st_size > 0:
                    try:
                        existing_profile_content = candidate.read_text(encoding="utf-8", errors="replace")
                        break
                    except Exception as exc:
                        logger.warning(f"Fehler beim Lesen des Steckbriefs {candidate}: {exc}")

        if existing_profile_content:
            # Sofort anzeigen!
            if self.app_steckbrief_markdown:
                self.app_steckbrief_markdown.set_content(existing_profile_content)
            if self.app_steckbrief_status:
                self.app_steckbrief_status.set_text("Vorhandener Steckbrief sofort geladen. Prüfe im Hintergrund auf Aktualisierungen...")
            if self.app_steckbrief_spinner:
                self.app_steckbrief_spinner.classes(remove='hidden')
            if self.app_steckbrief_refresh_btn:
                self.app_steckbrief_refresh_btn.set_visibility(True)
        elif email:
            if self.app_steckbrief_markdown:
                self.app_steckbrief_markdown.set_content(
                    f"### Kein lokaler Steckbrief vorhanden\nFür **{email}** existiert noch kein Steckbrief. Suche E-Mails und generiere Steckbrief im Hintergrund..."
                )
            if self.app_steckbrief_status:
                self.app_steckbrief_status.set_text("Generiere Steckbrief im Hintergrund...")
            if self.app_steckbrief_spinner:
                self.app_steckbrief_spinner.classes(remove='hidden')
            if self.app_steckbrief_refresh_btn:
                self.app_steckbrief_refresh_btn.set_visibility(True)
        else:
            if self.app_steckbrief_markdown:
                self.app_steckbrief_markdown.set_content(
                    f"### Kein Teilnehmer mit E-Mail-Adresse gefunden\nBetreff: {subject}\nTeilnehmer: {participant or '—'}"
                )
            if self.app_steckbrief_status:
                self.app_steckbrief_status.set_text("Keine Teilnehmer-E-Mail vorhanden.")
            if self.app_steckbrief_spinner:
                self.app_steckbrief_spinner.classes(add='hidden')
            if self.app_steckbrief_refresh_btn:
                self.app_steckbrief_refresh_btn.set_visibility(False)

        # 2. SOFORTIGE ANZEIGE DES STUDENTENORDNERS & DER SUMMARY
        class_paths = await run.io_bound(get_class_paths)
        cls = get_class_from_title(subject, class_paths, email, lastname)

        student_dir: Optional[Path] = None
        if cls in class_paths:
            student_dir = await run.io_bound(find_student_folder, Path(class_paths[cls]), lastname)

        if not student_dir:
            for bp_str in class_paths.values():
                student_dir = await run.io_bound(find_student_folder, Path(bp_str), lastname)
                if student_dir:
                    break

        self.app_student_dir = student_dir

        if student_dir and student_dir.exists():
            if self.app_student_folder_label:
                self.app_student_folder_label.set_text(str(student_dir))
            if self.app_btn_explorer:
                self.app_btn_explorer.set_visibility(True)
            if self.app_summary_refresh_btn:
                self.app_summary_refresh_btn.set_visibility(True)

            summary_file = student_dir / ".emails_summary.md"
            if summary_file.exists() and summary_file.stat().st_size > 0:
                summary_content = summary_file.read_text(encoding="utf-8", errors="replace")
                if self.app_summary_markdown:
                    self.app_summary_markdown.set_content(summary_content)
            else:
                if self.app_summary_markdown:
                    self.app_summary_markdown.set_content("*(Keine .emails_summary.md im Ordner vorhanden)*")

            # Dateiliste befüllen
            file_rows = []
            for f in sorted(student_dir.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        size_kb = f.stat().st_size / 1024
                        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                        mtime_str = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        file_rows.append({
                            'name': f.name,
                            'size': size_str,
                            'mtime': mtime_str,
                            'path': str(f.absolute())
                        })
                    except Exception:
                        pass
            if self.app_files_table:
                self.app_files_table.rows = file_rows
                self.app_files_table.update()
        else:
            if self.app_student_folder_label:
                self.app_student_folder_label.set_text("Kein Studentenordner gefunden.")
            if self.app_btn_explorer:
                self.app_btn_explorer.set_visibility(False)
            if self.app_summary_refresh_btn:
                self.app_summary_refresh_btn.set_visibility(False)
            if self.app_summary_markdown:
                self.app_summary_markdown.set_content("Kein Studentenordner gefunden.")
            if self.app_files_table:
                self.app_files_table.rows = []
                self.app_files_table.update()

        # 3. NACH DER ANZEIGE: HINTERGRUND-AKTUALISIERUNG STARTEN
        if email:
            asyncio.create_task(self._update_appointment_steckbrief_background(email))

    async def _update_appointment_steckbrief_background(self, email: str) -> None:
        """Aktualisiert den Steckbrief im Hintergrund, ohne die Benutzeroberfläche zu blockieren.

        Args:
            email (str): Die E-Mail-Adresse des Gesprächspartners.
        """
        logger.info(f"Hintergrund-Aktualisierung des Steckbriefs für {email} gestartet...")
        try:
            profiler = GUITools.profiler()
            updated_content = await run.io_bound(profiler.update_profile, email)

            # Prüfen ob der Nutzer inzwischen einen anderen Termin gewählt hat
            if self.app_participant_email != email:
                logger.info(f"Hintergrund-Update für {email} beendet, aber Teilnehmer hat gewechselt.")
                return

            if updated_content:
                if self.app_steckbrief_markdown:
                    self.app_steckbrief_markdown.set_content(updated_content)
                if self.app_steckbrief_status:
                    self.app_steckbrief_status.set_text("✅ Steckbrief ist auf dem neuesten Stand.")
                safe_notify(f"Steckbrief für {email} aktualisiert!", type='positive')
            else:
                if self.app_steckbrief_status:
                    self.app_steckbrief_status.set_text("✅ Steckbrief unverändert / aktuell.")
        except Exception as exc:
            logger.error(f"Fehler bei Hintergrund-Aktualisierung für {email}: {exc}")
            if self.app_participant_email == email and self.app_steckbrief_status:
                self.app_steckbrief_status.set_text(f"Hinweis: Aktualisierung nicht möglich ({exc})")
        finally:
            if self.app_participant_email == email and self.app_steckbrief_spinner:
                self.app_steckbrief_spinner.classes(add='hidden')

    async def trigger_manual_steckbrief_update(self) -> None:
        """Stößt die manuelle Aktualisierung des Steckbriefs für den aktuellen Termin an."""
        if not self.app_participant_email:
            safe_notify("Kein Teilnehmer mit E-Mail vorhanden.", type='warning')
            return
        if self.app_steckbrief_spinner:
            self.app_steckbrief_spinner.classes(remove='hidden')
        if self.app_steckbrief_status:
            self.app_steckbrief_status.set_text(f"Erzwinge Steckbrief-Generierung für {self.app_participant_email}...")

        try:
            profiler = GUITools.profiler()
            content = await run.io_bound(profiler.generate_profile, self.app_participant_email, True)
            if content:
                if self.app_steckbrief_markdown:
                    self.app_steckbrief_markdown.set_content(content)
                if self.app_steckbrief_status:
                    self.app_steckbrief_status.set_text("✅ Steckbrief erfolgreich neu generiert.")
                safe_notify("Steckbrief neu generiert!", type='positive')
            else:
                if self.app_steckbrief_status:
                    self.app_steckbrief_status.set_text("Konnte keinen Steckbrief erzeugen.")
        except Exception as exc:
            logger.error(f"Fehler bei manueller Steckbrief-Generierung: {exc}")
            if self.app_steckbrief_status:
                self.app_steckbrief_status.set_text(f"Fehler: {exc}")
        finally:
            if self.app_steckbrief_spinner:
                self.app_steckbrief_spinner.classes(add='hidden')

    async def trigger_summary_update(self) -> None:
        """Aktualisiert die Ordner-Zusammenfassung (.emails_summary.md) mittels LLM."""
        if not self.app_student_dir or not self.app_student_dir.exists():
            safe_notify("Kein gültiger Studentenordner vorhanden.", type='warning')
            return

        summarizer = GUITools.summarizer()
        if not summarizer:
            safe_notify("Summarizer ist nicht verfügbar.", type='warning')
            return

        if self.status_label:
            self.status_label.set_text("Erstelle neue Ordner-Zusammenfassung mit LLM...")
        try:
            email_files = list(self.app_student_dir.rglob("*.msg")) + list(self.app_student_dir.rglob("*.eml"))
            dated_emails = []
            parser = GUITools.parser()
            for f in email_files:
                try:
                    dated_emails.append((parser.get_email_date(f), f))
                except Exception:
                    dated_emails.append((datetime.min, f))
            dated_emails.sort(key=lambda x: x[0])

            conversation_content = ""
            for d, f in dated_emails:
                parsed = parser.parse(f)
                if parsed:
                    conversation_content += f"\n--- EMAIL VOM {d} ---\n{parsed}\n"

            new_summary = await run.io_bound(
                summarizer.summarize_email_conversation,
                self.app_student_dir.name,
                conversation_content
            )
            if new_summary:
                summary_file = self.app_student_dir / ".emails_summary.md"
                summary_file.write_text(new_summary, encoding="utf-8")
                if self.app_summary_markdown:
                    self.app_summary_markdown.set_content(new_summary)
                safe_notify("Ordner-Zusammenfassung erfolgreich aktualisiert!", type='positive')
                if self.status_label:
                    self.status_label.set_text("Ordner-Zusammenfassung aktualisiert.")
        except Exception as exc:
            logger.error(f"Fehler beim Aktualisieren der Zusammenfassung: {exc}")
            safe_notify(f"Fehler bei Zusammenfassung: {exc}", type='negative')
        finally:
            if self.status_label:
                self.status_label.set_text("Bereit.")

    def trigger_open_student_folder(self) -> None:
        """Öffnet den Studentenordner im Dateimanager."""
        if not self.app_student_dir:
            safe_notify("Kein Ordner vorhanden.", type='warning')
            return
        result = open_in_explorer(str(self.app_student_dir))
        if self.status_label:
            self.status_label.set_text(result)
        safe_notify(result, type='info')

    def on_student_file_clicked(self, row_data: Dict[str, Any]) -> None:
        """Öffnet die ausgewählte Datei aus dem Studentenordner.

        Args:
            row_data (Dict[str, Any]): Zeilendaten der Datei.
        """
        path_str = row_data.get('path', '')
        if not path_str:
            return
        res = open_file(path_str)
        if self.app_file_status:
            self.app_file_status.set_text(res)
        safe_notify(res, type='info')

    # -------------------------------------------------------------
    # ALLGEMEINE DETAIL- & ÖFFNEN-METHODEN
    # -------------------------------------------------------------
    async def display_email_details(self, row_data: Dict[str, Any], tab: int) -> None:
        """Lädt und zeigt die E-Mail-Details asynchron im entsprechenden Viewer.

        Args:
            row_data (Dict[str, Any]): Zeilendaten der Mail.
            tab (int): 1 für Tab 1, 2 für Tab 2, 3 für Tab 3.
        """
        path_str = row_data.get('path', '')
        if not path_str:
            return

        self.selected_email_path = path_str
        if self.status_label:
            self.status_label.set_text(f"Lade E-Mail: {Path(path_str).name}...")

        try:
            details = await run.io_bound(
                GUITools.parser().get_email_details,
                Path(path_str)
            )

            subject = details.get('subject', '(Kein Betreff)')
            from_name = details.get('from_name', '')
            from_email = details.get('from_email', '')
            date_str = str(details.get('date', ''))
            body = details.get('body', '*(Kein Textkörper)*')

            to_list = details.get('to', [])
            to_formatted = []
            for t in to_list:
                if isinstance(t, dict):
                    to_formatted.append(f"{t.get('name', '')} <{t.get('email', '')}>".strip())
                else:
                    to_formatted.append(str(t))

            meta_md = (
                f"**Von:** {from_name} &lt;{from_email}&gt;  \n"
                f"**An:** {', '.join(to_formatted) if to_formatted else '—'}  \n"
                f"**Datum:** {date_str}  \n"
                f"**Betreff:** {subject}  \n"
                f"**Datei:** `{Path(path_str).name}`"
            )

            if tab == 1:
                if self.tab1_viewer_title:
                    self.tab1_viewer_title.set_text(subject)
                if self.tab1_viewer_meta:
                    self.tab1_viewer_meta.set_content(meta_md)
                if self.tab1_viewer_body:
                    self.tab1_viewer_body.set_content(body)
                if self.tab1_btn_outlook:
                    self.tab1_btn_outlook.set_visibility(True)
                if self.tab1_btn_explorer:
                    self.tab1_btn_explorer.set_visibility(True)
            elif tab == 2:
                if self.tab2_viewer_meta:
                    self.tab2_viewer_meta.set_content(meta_md)
                if self.tab2_viewer_body:
                    self.tab2_viewer_body.set_content(body)
                if self.tab2_btn_outlook:
                    self.tab2_btn_outlook.set_visibility(True)
                if self.tab2_btn_explorer:
                    self.tab2_btn_explorer.set_visibility(True)
            elif tab == 3:
                if self.tab3_viewer_title:
                    self.tab3_viewer_title.set_text(subject)
                if self.tab3_viewer_meta:
                    self.tab3_viewer_meta.set_content(meta_md)
                if self.tab3_viewer_body:
                    self.tab3_viewer_body.set_content(body)
                if self.tab3_btn_outlook:
                    self.tab3_btn_outlook.set_visibility(True)
                if self.tab3_btn_explorer:
                    self.tab3_btn_explorer.set_visibility(True)

            if self.status_label:
                self.status_label.set_text(f"E-Mail geladen: {Path(path_str).name}")
        except Exception as exc:
            logger.error(f"Fehler beim Parsen der E-Mail {path_str}: {exc}")
            err_text = f"Fehler beim Laden: {exc}"
            if tab == 1 and self.tab1_viewer_body:
                self.tab1_viewer_body.set_content(err_text)
            elif tab == 2 and self.tab2_viewer_body:
                self.tab2_viewer_body.set_content(err_text)
            elif tab == 3 and self.tab3_viewer_body:
                self.tab3_viewer_body.set_content(err_text)

    def trigger_open_outlook(self, tab: int) -> None:
        """Öffnet die aktuell ausgewählte E-Mail in Outlook.

        Args:
            tab (int): Index des aufrufenden Tabs.
        """
        if not self.selected_email_path:
            safe_notify("Keine E-Mail ausgewählt!", type='warning')
            return
        result = open_in_outlook(self.selected_email_path)
        if self.status_label:
            self.status_label.set_text(result)
        safe_notify(result, type='info')

    def trigger_open_explorer(self, tab: int) -> None:
        """Öffnet den übergeordneten Ordner der E-Mail im Datei-Explorer.

        Args:
            tab (int): Index des aufrufenden Tabs.
        """
        if not self.selected_email_path:
            safe_notify("Keine E-Mail ausgewählt!", type='warning')
            return
        result = open_in_explorer(self.selected_email_path)
        if self.status_label:
            self.status_label.set_text(result)
        safe_notify(result, type='info')

    def _clear_all_tables(self) -> None:
        """Leert alle Tabellen und Textanzeigen bei leerer Klassenauswahl."""
        if self.recent_inbox_table:
            self.recent_inbox_table.rows = []
            self.recent_inbox_table.update()
        if self.recent_sent_table:
            self.recent_sent_table.rows = []
            self.recent_sent_table.update()
        if self.addresses_table:
            self.addresses_table.rows = []
            self.addresses_table.update()
        if self.person_inbox_table:
            self.person_inbox_table.rows = []
            self.person_inbox_table.update()
        if self.person_sent_table:
            self.person_sent_table.rows = []
            self.person_sent_table.update()
        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = '📥 Posteingang'
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = '📤 Gesendet'
            self.tab_person_sent.update()


def main() -> None:
    """Startet die NiceGUI-Applikation mit CLI-Parametern."""
    parser = argparse.ArgumentParser(description="NiceGUI E-Mail & Termin-Zentrale")
    parser.add_argument(
        "--native",
        action="store_true",
        help="Startet als natives Windows-Desktop-Fenster (via pywebview)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port für den lokalen Webserver (Standard: 8080)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Deaktiviert Auto-Reload (empfohlen für Production/Native)"
    )
    args = parser.parse_args()

    app_instance = EmailClassApp()
    app_instance.build_ui()

    logger.info(
        f"Starte NiceGUI-Interface (native={args.native}, port={args.port})..."
    )

    ui.run(
        title="Academic Memory — E-Mail & Termin-Zentrale",
        native=args.native,
        port=args.port,
        reload=not args.no_reload,
        window_size=(1400, 900) if args.native else None
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
