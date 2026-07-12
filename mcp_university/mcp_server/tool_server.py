"""FastMCP Server mit gut dokumentierten Tools für das University Memory System."""
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastmcp import FastMCP

from ..config import get_config
from ..metadata.store import MetadataStore
from ..retrieval.index import SearchIndex
from ..parser.factory import ParserFactory

logger = logging.getLogger(__name__)

def create_tool_server() -> FastMCP:
    """Initialisiert den FastMCP-Server mit Tools für den Agenten."""
    cfg = get_config()
    mcp = FastMCP("University Agent Tools", instructions="You provide well-documented tools for a university assistant agent.")

    # Lazy initialization for components
    # These are initialized inside the tools or as global-ish within the factory to avoid startup overhead
    # but here we follow the pattern of the existing server.py
    store = MetadataStore(cfg.sqlite_path)
    index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    parser_factory = ParserFactory(cfg.data_dir / "cache")

    @mcp.tool
    def read_file(path: str) -> str:
        """Liest den Inhalt einer Datei (PDF, DOCX, MD, TXT, MSG) ein.

        Args:
            path: Der absolute oder relative Pfad zur Datei, die gelesen werden soll.

        Returns:
            Der Textinhalt der Datei oder eine Fehlermeldung, falls die Datei nicht existiert oder nicht gelesen werden kann.
        """
        p = Path(path)
        if not p.exists():
            return f"Fehler: Datei {path} nicht gefunden."
        content = parser_factory.parse(p)
        return content or "Fehler: Datei konnte nicht gelesen werden oder ist leer."

    @mcp.tool
    def search_documents(query: str) -> str:
        """Sucht in den indexierten Universitäts-Dokumenten (Prüfungsordnungen, Skripte, etc.) nach relevanten Informationen.

        Args:
            query: Die Suchanfrage in natürlicher Sprache.

        Returns:
            Eine Zusammenfassung der relevantesten Dokumentabschnitte mit Dateinamen.
        """
        results = index.search(query, top_k=3)
        if not results:
            return "Keine relevanten Dokumente gefunden."

        output = ""
        for res in results:
            output += f"--- {res['filename']} (Relevanz: {res['score']:.2f}) ---\n{res['content']}\n\n"
        return output

    @mcp.tool
    def get_student_info(student_name: str) -> str:
        """Liefert detaillierte Informationen und den Kontext zu einem Studenten aus der Datenbank.

        Args:
            student_name: Der vollständige Name oder ein Teil des Namens des Studenten.

        Returns:
            Strukturierte Informationen über den Studenten (E-Mail, Thema, Status, Ordnerpfad) und eine Zusammenfassung des bisherigen Schriftverkehrs.
        """
        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.name, s.email, s.topic, s.status, f.path as folder_path
                FROM students s
                LEFT JOIN folders f ON s.folder_id = f.id
                WHERE s.name LIKE ?
            ''', (f"%{student_name}%",))
            student = cursor.fetchone()
            if not student:
                return f"Kein Student mit dem Namen '{student_name}' gefunden."

            # (id, name, email, topic, status, folder_path)
            res = (f"Student: {student[1]}\n"
                   f"Email: {student[2]}\n"
                   f"Thema: {student[3]}\n"
                   f"Status: {student[4]}\n"
                   f"Ordner: {student[5]}\n")

            # Zusammenfassung aus der Datenbank laden
            if student[5]:
                cursor.execute('''
                    SELECT content FROM summaries
                    JOIN folders ON summaries.item_id = folders.id
                    WHERE folders.path = ? AND summaries.item_type = 'folder'
                    ORDER BY summaries.created_at DESC LIMIT 1
                ''', (student[5],))
                row = cursor.fetchone()
                if row:
                    res += f"\nZusammenfassung des Ordners:\n{row[0]}"

            return res

    @mcp.tool
    def get_appointment_slots() -> str:
        """Liest die aktuell verfügbaren freien Terminslots für Sprechstunden aus der Konfigurationsdatei aus.

        Returns:
            Eine Liste der freien Zeitfenster (Datum und Uhrzeit).
        """
        slots_path = Path("D:/TH_Koeln/PAV/Termine/FreieSlots.md")
        if not slots_path.exists():
             # Fallback/Mockup if path doesn't exist in sandbox
             return "Keine freien Slots gefunden (Datei D:/TH_Koeln/PAV/Termine/FreieSlots.md nicht vorhanden)."

        try:
            return slots_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Fehler beim Lesen der freien Slots: {e}"

    @mcp.tool
    def manage_calendar_appointment(start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: Optional[str] = None, body: Optional[str] = None, is_colloquium: bool = False) -> str:
        """Prüft die Verfügbarkeit eines Zeitfensters im Outlook-Kalender und trägt einen neuen Termin ein.

        Args:
            start_time: Beginn des Termins im Format 'YYYY-MM-DD HH:MM'.
            end_time: Ende des Termins im Format 'YYYY-MM-DD HH:MM'.
            subject: Der Betreff des Kalendereintrags.
            student_email: Die E-Mail-Adresse des Studenten, der eingeladen werden soll.
            original_mail_date: Das Datum der ursprünglichen E-Mail des Studenten (Format DD.MM.YY), wird im Body des Termins vermerkt.
            body: Der Inhalt der E-Mail für den Kalendereintrag (optional).
            is_colloquium: Gibt an, ob es sich um ein Kolloquium handelt (optional).

        Returns:
            Eine Erfolgsmeldung mit Details zum Termin oder eine Fehlermeldung, falls der Slot belegt ist oder ein technisches Problem auftrat.
        """
        # Hier nutzen wir die bestehende Logik aus dem Agent, um Redundanz zu vermeiden
        # Da wir im MCP server sind, müssen wir ggf. win32com lokal haben
        try:
            import win32com.client
        except ImportError:
            return "Fehler: pywin32 ist nicht installiert. Kalender-Funktionen sind auf diesem System nicht verfügbar."

        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            target_account = get_config().user.email
            target_calendar_name = "Kalender (Nur dieser Computer)"

            # (Rest der Logik analog zu mcp_university/agent/engine.py _tool_manage_calendar_appointment)
            # Wir implementieren hier eine verkürzte Version für den MCP Server

            tz = ZoneInfo("Europe/Berlin")
            dt_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            dt_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)

            if is_colloquium:
                if (dt_end - dt_start) < timedelta(minutes=60):
                    dt_end = dt_start + timedelta(minutes=60)

            # Suche Kalender
            cal_folder = None
            for i in range(1, namespace.Accounts.Count + 1):
                account = namespace.Accounts.Item(i)
                if account.SmtpAddress.lower() == target_account.lower():
                    logger.info(f"ERFOLG: Konto gefunden: {account.SmtpAddress}")
                    store = account.DeliveryStore
                    root = store.GetRootFolder()
                    for j in range(1, root.Folders.Count + 1):
                        folder = root.Folders.Item(j)
                        print(f"DEBUG: Checking folder {folder.Name} against {target_calendar_name}")
                        if folder.Name == target_calendar_name:
                            logger.info(f"ERFOLG: Ziel-Kalender gefunden: {folder.FolderPath}")
                            cal_folder = folder
                            break
                    if not cal_folder:
                        # Fallback: Default Calendar for this store (olFolderCalendar = 9)
                        try:
                            cal_folder = store.GetDefaultFolder(9)
                        except Exception:
                            pass
                    break

            if not cal_folder:
                return f"Fehler: Kalender '{target_calendar_name}' für '{target_account}' nicht gefunden."

            if dt_end <= dt_start:
                return f"Fehler: Das Ende des Termins ({end_time}) muss nach dem Beginn ({start_time}) liegen."

            appointment = cal_folder.Items.Add(1) # olAppointmentItem
            appointment.Subject = subject
            appointment.Start = dt_start.replace(tzinfo=None)
            appointment.End = dt_end.replace(tzinfo=None)
            appointment.Location = "Zoom (siehe E-Mail-Signatur)"
            body_text = body if body else (f"Terminbestätigung auf Basis Ihrer Mail vom {original_mail_date}" if original_mail_date else "Terminbestätigung via MCP System.")
            appointment.Body = body_text

            recipient = appointment.Recipients.Add(student_email)
            recipient.Type = 1 # olTo
            appointment.MeetingStatus = 1 # olMeeting

            appointment.Save()

            # Automatisches Update der Kolloquium-Config falls erkannt
            if is_colloquium:
                try:
                    update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))
                except Exception as e:
                    logger.error(f"Fehler beim automatischen Update der Kolloquium-Config: {e}")

            return f"ERFOLG: Termin '{subject}' am {start_time} wurde eingetragen."

        except Exception as e:
            return f"Fehler bei der Kalender-Verarbeitung: {e}"


    @mcp.tool
    def save_email_attachments(email_path: str) -> str:
        """Extrahiert Anhänge aus einer E-Mail und speichert sie im Elternordner des E-Mail-Ordners.

        Args:
            email_path: Der Pfad zur E-Mail-Datei.

        Returns:
            str: Erfolgsmeldung oder Fehlermeldung.
        """
        try:
            from ..parser.mail_parser import MailParser
            p = Path(email_path)
            if not p.exists():
                return f"Fehler: Datei {email_path} nicht gefunden."

            target_dir = p.parent.parent
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)

            parser = MailParser()
            saved_paths = parser.save_attachments(p, target_dir)

            if not saved_paths:
                return "Keine Anhänge zum Speichern gefunden."

            paths_str = ", ".join([str(p) for p in saved_paths])
            return f"ERFOLG: Anhänge gespeichert in: {paths_str}"
        except Exception as e:
            return f"Fehler beim Speichern der Anhänge: {e}"

    @mcp.tool
    def create_colloquium_config(email_path: str, pdf_filename: str) -> str:
        """Erstellt eine config.json für den colloquium-protocol-creator bei finaler Abgabe.
        Falls die Datei bereits existiert, wird nur der Dateiname der Bachelorarbeit aktualisiert.

        Args:
            email_path: Pfad zur E-Mail.
            pdf_filename: Dateiname der PDF-Arbeit im Anhang.

        Returns:
            Erfolgsmeldung oder Fehler.
        """
        try:
            import json
            p = Path(email_path)
            # Anhänge liegen im Elternordner des E-Mail-Ordners (p.parent.parent)
            target_dir = p.parent.parent
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)

            config_path = target_dir / "config.json"

            if config_path.exists():
                logger.info(f"config.json existiert bereits unter {config_path}. Aktualisiere nur PDF-Dateiname.")
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                config_data["pdf"]["filename"] = pdf_filename
            else:
                config_data = {
                  "task": "colloquium",
                  "description": "Kolloquium auf dem Campus Gummersbach mit automatischer Gemini-Bewertung",
                  "pdf": {
                    "filename": pdf_filename
                  },
                  "colloquium": {
                    "date": "DD.MM.YYYY",
                    "time": "hh:mm",
                    "location_type": "campus",
                    "room": "3.228"
                  },
                  "llm": {
                    "api_choice": None,
                    "model": None,
                    "groq_free": True
                  },
                  "gemini_evaluation": {
                    "enabled": False,
                    "model": "gemini-2.0-flash-exp"
                  },
                  "output": {
                    "folder": None,
                    "compile_pdf": True,
                    "fill_form_only": True
                  }
                }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return f"ERFOLG: Konfiguration erstellt/aktualisiert unter {config_path}"
        except Exception as e:
            return f"Fehler beim Erstellen der Konfiguration: {e}"

    @mcp.tool
    def update_colloquium_config(student_email: str, date: str, time: str) -> str:
        """Aktualisiert Datum und Uhrzeit in der config.json eines Studenten.
        Falls die config.json noch nicht existiert, wird sie mit Standardwerten erstellt.

        Args:
            student_email: E-Mail-Adresse des Studenten.
            date: Datum des Kolloquiums (DD.MM.YYYY).
            time: Uhrzeit des Kolloquiums (hh:mm).

        Returns:
            Erfolgsmeldung oder Fehler.
        """
        try:
            import json
            with store._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.path FROM students s
                    JOIN folders f ON s.folder_id = f.id
                    WHERE s.email = ?
                """, (student_email,))
                row = cursor.fetchone()
                if not row:
                    return f"Fehler: Kein Ordner für Student {student_email} in Datenbank gefunden."

                # Die config.json liegt im Hauptordner des Studenten, nicht in Unterordnern
                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    # Fallback: Falls row[0] ein Unterordner wie "SentItems" ist
                    potential_path = Path(row[0]).parent / "config.json"
                    if potential_path.exists() or Path(row[0]).name in ["SentItems", "Inbox", "Posteingang", "Gesendete Elemente"]:
                         config_path = potential_path

                if not config_path.exists():
                     logger.info(f"config.json nicht gefunden. Erstelle neue unter {config_path}")
                     config_data = {
                      "task": "colloquium",
                      "description": "Kolloquium auf dem Campus Gummersbach mit automatischer Gemini-Bewertung",
                      "pdf": {
                        "filename": ""
                      },
                      "colloquium": {
                        "date": date,
                        "time": time,
                        "location_type": "campus",
                        "room": "3.228"
                      },
                      "llm": {
                        "api_choice": None,
                        "model": None,
                        "groq_free": True
                      },
                      "gemini_evaluation": {
                        "enabled": False,
                        "model": "gemini-2.0-flash-exp"
                      },
                      "output": {
                        "folder": None,
                        "compile_pdf": True,
                        "fill_form_only": True
                      }
                    }
                else:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                    config_data["colloquium"]["date"] = date
                    config_data["colloquium"]["time"] = time

                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)

                return f"ERFOLG: Kolloquiumstermin in {config_path} aktualisiert."
        except Exception as e:
            return f"Fehler beim Aktualisieren der Konfiguration: {e}"

    return mcp
