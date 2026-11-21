"""Modernes NiceGUI-basiertes Interface für die E-Mail-Suche nach E-Mail-Klassen.

Bietet schnelle Tabellen (Quasar/AG-Grid), echte Split-Pane-Ansichten,
nicht-blockierende Hintergrund-Tasks für Steckbriefe und optionalen
nativen Windows-Desktop-Modus (via pywebview).
"""

import os
import platform
import subprocess
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from nicegui import ui, run

from mcp_university.utils.email_search import EmailSearchEngine
from academic_parser.mail_parser import MailParser
from mcp_university.summarizer.profiler import PersonProfiler

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
    """Öffnet den übergeordneten Ordner der Datei im Explorer.

    Args:
        filepath (str): Absoluter Pfad zur E-Mail-Datei.

    Returns:
        str: Statusmeldung über das Ergebnis.
    """
    if not filepath or not Path(filepath).exists():
        msg = f"Datei nicht gefunden: {filepath}"
        logger.warning(msg)
        return msg

    folder = str(Path(filepath).parent.absolute())
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


class EmailClassApp:
    """Haupt-Applikationsklasse für das NiceGUI E-Mail-Interface."""

    def __init__(self) -> None:
        """Initialisiert die Anwendungszustände und Datenstrukturen."""
        self.selected_class: str = ""
        self.selected_address: str = ""
        self.selected_email_path: str = ""

        # UI-Komponenten Referenzen
        self.class_select: Optional[ui.select] = None
        self.status_label: Optional[ui.label] = None

        # Tab 1 Komponenten
        self.recent_inbox_table: Optional[ui.table] = None
        self.recent_sent_table: Optional[ui.table] = None
        self.tab1_viewer_title: Optional[ui.label] = None
        self.tab1_viewer_meta: Optional[ui.markdown] = None
        self.tab1_viewer_body: Optional[ui.markdown] = None
        self.tab1_btn_outlook: Optional[ui.button] = None
        self.tab1_btn_explorer: Optional[ui.button] = None

        # Tab 2 Komponenten
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

    def build_ui(self) -> None:
        """Erstellt die vollständige Benutzeroberfläche in NiceGUI."""
        # Basis-Styling und Icons
        ui.colors(primary='#1976D2', secondary='#26A69A', accent='#9C27B0')

        with ui.header().classes('items-center justify-between bg-slate-800 text-white shadow-md px-6 py-2'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('mail', size='2rem').classes('text-blue-400')
                with ui.column().classes('gap-0'):
                    ui.label('Academic Memory — E-Mail Klassen').classes('text-lg font-bold')
                    ui.label('Lokale E-Mail-Klassen, Steckbriefe & Schnellzugriff').classes('text-xs text-slate-300')

            with ui.row().classes('items-center gap-4'):
                email_classes = GUITools.engine().get_email_classes()
                self.class_select = ui.select(
                    options=email_classes,
                    label='E-Mail-Klasse wählen',
                    with_input=True,
                    on_change=self.on_class_selected
                ).classes('w-72 bg-white rounded').props('dense outlined clearable')

                ui.dark_mode().bind_value(ui.switch('Dark', value=False).classes('text-white text-xs'))

        # Tabs Navigation
        with ui.tabs().classes('w-full border-b bg-slate-50') as tabs:
            tab_recent = ui.tab('🕒 Letzte Mails der Klasse', icon='schedule')
            tab_address = ui.tab('👥 Nach E-Mail-Adresse & Steckbrief', icon='people')

        with ui.tab_panels(tabs, value=tab_recent).classes('w-full h-full p-4'):
            # TAB 1: Letzte Mails
            with ui.tab_panel(tab_recent):
                self._build_tab_recent()

            # TAB 2: Nach Adresse & Steckbrief
            with ui.tab_panel(tab_address):
                self._build_tab_address()

        # Footer mit Statuszeile
        with ui.footer().classes('bg-slate-100 text-slate-700 text-xs px-4 py-1.5 border-t justify-between items-center'):
            self.status_label = ui.label('Bereit. Bitte wähle oben eine E-Mail-Klasse aus.')
            ui.label('MCP University • Offline-First').classes('text-slate-400 font-mono')

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

    async def on_class_selected(self, event: Any) -> None:
        """Reagiert auf die Auswahl einer E-Mail-Klasse und befüllt Tabellen nicht-blockierend.

        Args:
            event (Any): Event-Objekt der Select-Komponente.
        """
        selected_val = event.value if hasattr(event, 'value') else event
        self.selected_class = selected_val or ""

        if not self.selected_class:
            self._clear_all_tables()
            self.status_label.set_text("Keine E-Mail-Klasse ausgewählt.")
            return

        self.status_label.set_text(f"Lade Daten für E-Mail-Klasse '{self.selected_class}'...")

        # 1. Tab 1: Letzte 10 Mails
        recent_inbox, recent_sent = await run.io_bound(
            GUITools.engine().get_recent_emails_for_class,
            self.selected_class,
            10
        )

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
        self.person_inbox_table.rows = []
        self.person_inbox_table.update()
        self.person_sent_table.rows = []
        self.person_sent_table.update()
        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = '📥 Posteingang'
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = '📤 Gesendet'
            self.tab_person_sent.update()
        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = '📥 Posteingang'
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = '📤 Gesendet'
            self.tab_person_sent.update()
        self.steckbrief_markdown.set_content(
            "Wähle oben eine Person aus der Adressliste aus."
        )
        self.steckbrief_btn.set_visibility(False)
        self.tab2_viewer_meta.set_content("")
        self.tab2_viewer_body.set_content("")
        self.tab2_btn_outlook.set_visibility(False)
        self.tab2_btn_explorer.set_visibility(False)

        status_msg = (
            f"Klasse '{self.selected_class}': {len(addresses)} Personen, "
            f"{len(recent_inbox)} Inbox-Mails, {len(recent_sent)} Sent-Mails geladen."
        )
        self.status_label.set_text(status_msg)
        ui.notify(status_msg, type='info', position='bottom-right')

    async def on_address_selected(self, row_data: Dict[str, Any]) -> None:
        """Wird aufgerufen, wenn eine Person in der Adressliste angeklickt wird.

        Args:
            row_data (Dict[str, Any]): Zeilendaten der ausgewählten Person.
        """
        email_addr = row_data.get('email', '')
        self.selected_address = email_addr

        if not email_addr:
            return

        self.status_label.set_text(f"Lade Details & E-Mails für: {email_addr}...")

        # 1. Steckbrief prüfen
        profiler = GUITools.profiler()
        profile_file = profiler.storage_path / f"{email_addr}.md"

        if profile_file.exists() and profile_file.stat().st_size > 0:
            try:
                content = profile_file.read_text(encoding="utf-8")
                self.steckbrief_markdown.set_content(content)
                self.steckbrief_btn.set_visibility(False)
            except Exception as e:
                self.steckbrief_markdown.set_content(f"Fehler beim Laden des Steckbriefs: {e}")
                self.steckbrief_btn.set_visibility(True)
        else:
            self.steckbrief_markdown.set_content(
                f"### Kein Steckbrief vorhanden\nFür **{email_addr}** existiert noch kein Steckbrief."
            )
            self.steckbrief_btn.set_text("Steckbrief generieren")
            self.steckbrief_btn.set_visibility(True)

        # 2. Mails dieser Person laden
        inbox_mails, sent_mails = await run.io_bound(
            GUITools.engine().get_emails_for_class_and_address,
            self.selected_class,
            email_addr
        )

        self.person_inbox_table.rows = [
            {
                'date': str(m.get('date', ''))[:10],
                'subject': m.get('subject', '(Kein Betreff)'),
                'path': m.get('path', '')
            }
            for m in inbox_mails
        ]
        self.person_inbox_table.update()

        self.person_sent_table.rows = [
            {
                'date': str(m.get('date', ''))[:10],
                'subject': m.get('subject', '(Kein Betreff)'),
                'path': m.get('path', '')
            }
            for m in sent_mails
        ]
        self.person_sent_table.update()

        # Tab-Header mit Anzahl aktualisieren
        if self.tab_person_inbox:
            self.tab_person_inbox._props['label'] = f"📥 Posteingang ({len(inbox_mails)})"
            self.tab_person_inbox.update()
        if self.tab_person_sent:
            self.tab_person_sent._props['label'] = f"📤 Gesendet ({len(sent_mails)})"
            self.tab_person_sent.update()

        self.status_label.set_text(
            f"Person '{email_addr}': {len(inbox_mails)} Inbox- und {len(sent_mails)} Sent-Mails."
        )

    async def generate_steckbrief(self) -> None:
        """Erzeugt im Hintergrund einen Steckbrief für die gewählte E-Mail-Adresse."""
        if not self.selected_address:
            ui.notify("Keine Person ausgewählt!", type='warning')
            return

        self.steckbrief_spinner.classes(remove='hidden')
        self.steckbrief_btn.disable()
        self.status_label.set_text(f"Generiere Steckbrief für {self.selected_address} mit LLM...")

        try:
            profile_content = await run.io_bound(
                GUITools.profiler().generate_profile,
                self.selected_address,
                True  # force_update
            )
            if profile_content:
                self.steckbrief_markdown.set_content(profile_content)
                self.steckbrief_btn.set_visibility(False)
                ui.notify(f"Steckbrief für {self.selected_address} erfolgreich erstellt!", type='positive')
            else:
                self.steckbrief_markdown.set_content(
                    f"Fehler: Für **{self.selected_address}** konnte kein Steckbrief erzeugt werden."
                )
                self.steckbrief_btn.set_text("Erneut versuchen")
                self.steckbrief_btn.enable()
        except Exception as exc:
            logger.error(f"Fehler bei Steckbrief-Generierung: {exc}")
            self.steckbrief_markdown.set_content(f"Fehler: {exc}")
            self.steckbrief_btn.enable()
        finally:
            self.steckbrief_spinner.classes(add='hidden')
            self.status_label.set_text("Bereit.")

    async def display_email_details(self, row_data: Dict[str, Any], tab: int) -> None:
        """Lädt und zeigt die E-Mail-Details asynchron im entsprechenden Viewer.

        Args:
            row_data (Dict[str, Any]): Zeilendaten der Mail.
            tab (int): 1 für Tab 1 (Letzte Mails), 2 für Tab 2 (Adresse).
        """
        path_str = row_data.get('path', '')
        if not path_str:
            return

        self.selected_email_path = path_str
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
                self.tab1_viewer_title.set_text(subject)
                self.tab1_viewer_meta.set_content(meta_md)
                self.tab1_viewer_body.set_content(body)
                self.tab1_btn_outlook.set_visibility(True)
                self.tab1_btn_explorer.set_visibility(True)
            else:
                self.tab2_viewer_meta.set_content(meta_md)
                self.tab2_viewer_body.set_content(body)
                self.tab2_btn_outlook.set_visibility(True)
                self.tab2_btn_explorer.set_visibility(True)

            self.status_label.set_text(f"E-Mail geladen: {Path(path_str).name}")
        except Exception as exc:
            logger.error(f"Fehler beim Parsen der E-Mail {path_str}: {exc}")
            err_text = f"Fehler beim Laden: {exc}"
            if tab == 1:
                self.tab1_viewer_body.set_content(err_text)
            else:
                self.tab2_viewer_body.set_content(err_text)

    def trigger_open_outlook(self, tab: int) -> None:
        """Öffnet die aktuell ausgewählte E-Mail in Outlook.

        Args:
            tab (int): Index des aufrufenden Tabs.
        """
        if not self.selected_email_path:
            ui.notify("Keine E-Mail ausgewählt!", type='warning')
            return
        result = open_in_outlook(self.selected_email_path)
        self.status_label.set_text(result)
        ui.notify(result, type='info')

    def trigger_open_explorer(self, tab: int) -> None:
        """Öffnet den übergeordneten Ordner der E-Mail im Datei-Explorer.

        Args:
            tab (int): Index des aufrufenden Tabs.
        """
        if not self.selected_email_path:
            ui.notify("Keine E-Mail ausgewählt!", type='warning')
            return
        result = open_in_explorer(self.selected_email_path)
        self.status_label.set_text(result)
        ui.notify(result, type='info')

    def _clear_all_tables(self) -> None:
        """Leert alle Tabellen und Textanzeigen bei leerer Klassenauswahl."""
        self.recent_inbox_table.rows = []
        self.recent_inbox_table.update()
        self.recent_sent_table.rows = []
        self.recent_sent_table.update()
        self.addresses_table.rows = []
        self.addresses_table.update()
        self.person_inbox_table.rows = []
        self.person_inbox_table.update()
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
    parser = argparse.ArgumentParser(description="NiceGUI E-Mail-Klassen Browser")
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
        title="Academic Memory — E-Mail Klassen",
        native=args.native,
        port=args.port,
        reload=not args.no_reload,
        window_size=(1400, 900) if args.native else None
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
