"""Modul für den Agenten mit Tool-Calling-Unterstützung."""
import logging
from typing import List, Dict, Callable
from pathlib import Path
from datetime import datetime
import ollama

from ..config import get_config
from ..parser.factory import ParserFactory
from ..retrieval.index import SearchIndex
from ..metadata.store import MetadataStore

logger = logging.getLogger(__name__)

class Agent:
    """Agent, der Tool-Calling mittels Ollama unterstützt."""

    def __init__(self, model: str = None, base_url: str = None):
        """Initialisiert den Agenten.

        Args:
            model (str, optional): Name des Ollama-Modells.
            base_url (str, optional): Basis-URL des Ollama-Servers.
        """
        self.cfg = get_config()
        self.model = model or self.cfg.llm.model
        self.base_url = str(base_url or self.cfg.llm.base_url)
        self.client = ollama.Client(host=self.base_url)

        self.parser_factory = ParserFactory(self.cfg.data_dir / "cache")
        self.store = MetadataStore(self.cfg.sqlite_path)
        self.index = SearchIndex(str(self.cfg.qdrant_path), self.cfg.embeddings.model, store=self.store)

        self.available_tools: Dict[str, Callable] = {
            "read_file": self._tool_read_file,
            "search_documents": self._tool_search_documents,
            "get_student_info": self._tool_get_student_info,
            "get_appointment_slots": self._tool_get_appointment_slots,
            "manage_calendar_appointment": self._tool_manage_calendar_appointment
        }

        self.tools_definition = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Liest den Inhalt einer Datei (PDF, DOCX, MD, TXT, MSG) ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Der Pfad zur Datei."
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Sucht in den indexierten Universitäts-Dokumenten nach Informationen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Die Suchanfrage."
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_info",
                    "description": "Liefert Informationen und Kontext zu einem Studenten.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_name": {
                                "type": "string",
                                "description": "Name oder Teilname des Studenten."
                            }
                        },
                        "required": ["student_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_appointment_slots",
                    "description": "Liest die aktuell verfügbaren freien Terminslots aus einer Datei.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_calendar_appointment",
                    "description": "Prüft die Verfügbarkeit eines Slots und trägt bei Erfolg einen Kalendertermin ein und lädt den Studenten ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {
                                "type": "string",
                                "description": "Beginn des Termins im Format 'YYYY-MM-DD HH:MM'."
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Ende des Termins im Format 'YYYY-MM-DD HH:MM'."
                            },
                            "subject": {
                                "type": "string",
                                "description": "Der Betreff des Kalendereintrags."
                            },
                            "student_email": {
                                "type": "string",
                                "description": "Die E-Mail-Adresse des Studenten, der eingeladen werden soll."
                            }
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            }
        ]

    def _tool_read_file(self, path: str) -> str:
        """Liest eine Datei ein.

        Args:
            path: Der Pfad zur Datei.

        Returns:
            str: Dateiinhalt oder Fehlermeldung.
        """
        p = Path(path)
        if not p.exists():
            return f"Fehler: Datei {path} nicht gefunden."
        content = self.parser_factory.parse(p)
        return content or "Fehler: Datei konnte nicht gelesen werden oder ist leer."

    def _tool_search_documents(self, query: str) -> str:
        """Sucht im Index.

        Args:
            query: Die Suchanfrage.

        Returns:
            str: Suchergebnisse oder Hinweis.
        """
        results = self.index.search(query, top_k=3)
        if not results:
            return "Keine relevanten Dokumente gefunden."

        output = ""
        for res in results:
            output += f"--- {res['filename']} (Score: {res['score']:.2f}) ---\n{res['content']}\n\n"
        return output

    def _tool_get_student_info(self, student_name: str) -> str:
        """Holt Studentendaten.

        Args:
            student_name: Name des Studenten.

        Returns:
            str: Informationen zum Studenten.
        """
        with self.store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, f.path as folder_path FROM students s
                LEFT JOIN folders f ON s.folder_id = f.id
                WHERE s.name LIKE ?
            ''', (f"%{student_name}%",))
            student = cursor.fetchone()
            if not student:
                return f"Kein Student mit dem Namen {student_name} gefunden."

            # (id, name, email, topic, status, folder_id, folder_path)
            context = f"Student: {student[1]}\nEmail: {student[2]}\nThema: {student[3]}\nStatus: {student[4]}\nOrdner: {student[6]}\n"
            return context

    def _tool_get_appointment_slots(self) -> str:
        """Liest die Datei mit den freien Terminslots ein.

        Returns:
            str: Freie Slots als Markdown oder Fehlermeldung.
        """
        path = Path(r"D:\TH_Koeln\academic-memory-mcp\data\free_slots.md")
        if not path.exists():
            return "Fehler: Die Datei mit freien Slots wurde nicht gefunden. Das Makro Freeslotexport.bas muss eventuell zuerst ausgeführt werden."
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Fehler beim Lesen der freien Slots: {e}"

    def _tool_manage_calendar_appointment(self, start_time: str, end_time: str, subject: str, student_email: str) -> str:
        """Prüft einen Slot und trägt einen Kalendertermin ein, falls frei.

        Args:
            start_time: Beginn des Termins ('YYYY-MM-DD HH:MM').
            end_time: Ende des Termins ('YYYY-MM-DD HH:MM').
            subject: Betreff des Kalendereintrags.
            student_email: E-Mail-Adresse des Studenten.

        Returns:
            str: Erfolgs- oder Fehlermeldung.
        """
        try:
            import win32com.client
        except ImportError:
            return "Fehler: pywin32 ist nicht installiert. Kalender-Funktionen sind nicht verfügbar."

        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")

            target_account = "daniel.gaida@th-koeln.de"
            target_calendar_name = "Kalender (Nur dieser Computer)"

            # Kalender suchen
            cal_folder = None
            for i in range(1, namespace.Accounts.Count + 1):
                account = namespace.Accounts.Item(i)
                if account.SmtpAddress.lower() == target_account.lower():
                    store = account.DeliveryStore
                    root = store.GetRootFolder()
                    for j in range(1, root.Folders.Count + 1):
                        folder = root.Folders.Item(j)
                        if folder.Name == target_calendar_name:
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

            # Zielordner für Entwürfe suchen (Work in Progress)
            target_folder_name = "Work in Progress"
            target_folder = None
            try:
                for store in namespace.Stores:
                    if store.DisplayName.lower() == target_account.lower():
                        root = store.GetRootFolder()
                        for folder in root.Folders:
                            if folder.Name.lower() == target_folder_name.lower():
                                target_folder = folder
                                break
                        if not target_folder:
                            for folder in root.Folders:
                                if folder.Name.lower() in ["posteingang", "inbox"]:
                                    for sub in folder.Folders:
                                        if sub.Name.lower() == target_folder_name.lower():
                                            target_folder = sub
                                            break
                                if target_folder:
                                    break
                        if target_folder:
                            break
            except Exception as e:
                logger.warning(f"Fehler beim Suchen des Zielordners '{target_folder_name}': {e}")

            # Slot prüfen
            dt_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            dt_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M")

            outlook_start = dt_start.strftime("%m/%d/%Y %H:%M %p")
            outlook_end = dt_end.strftime("%m/%d/%Y %H:%M %p")

            filter_str = f'[Start] < "{outlook_end}" AND [End] > "{outlook_start}"'
            items = cal_folder.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]")
            restricted_items = items.Restrict(filter_str)

            # Ignore all-day events as in the VBA macro
            is_free = True
            for item in restricted_items:
                try:
                    if not item.AllDayEvent:
                        is_free = False
                        break
                except Exception:
                    continue

            if not is_free:
                return f"Fehler: Der Slot von {start_time} bis {end_time} ist bereits belegt."

            # Termin eintragen
            # Wenn automatisch gesendet werden soll, direkt im Kalender erstellen
            # Ansonsten versuchen, in "Work in Progress" zu erstellen, falls vorhanden
            auto_send = self.cfg.calendar.send_invitations_automatically

            if not auto_send and target_folder:
                appointment = target_folder.Items.Add(1) # 1 = olAppointmentItem
                logger.info(f"Erstelle Termin-Entwurf in '{target_folder_name}'.")
            else:
                appointment = cal_folder.Items.Add(1) # 1 = olAppointmentItem
                if not auto_send:
                    logger.warning(f"Zielordner '{target_folder_name}' nicht gefunden. Erstelle im Standard-Kalender.")

            appointment.Subject = subject
            appointment.Start = dt_start
            appointment.End = dt_end
            appointment.Location = "Zoom (siehe E-Mail-Signatur)"
            appointment.Body = "Terminbestätigung via MCP University System."

            # Einladung vorbereiten
            recipient = appointment.Recipients.Add(student_email)
            recipient.Type = 1 # 1 = olTo
            appointment.MeetingStatus = 1 # 1 = olMeeting

            appointment.Save()

            if auto_send:
                appointment.Send()
                return f"ERFOLG: Termin '{subject}' am {start_time} wurde eingetragen und Einladung an {student_email} gesendet."
            else:
                return f"ERFOLG: Termin-Entwurf '{subject}' am {start_time} wurde in '{target_folder_name if target_folder else cal_folder.Name}' gespeichert (nicht gesendet)."

        except Exception as e:
            return f"Fehler bei der Kalender-Verarbeitung: {e}"

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Führt eine Chat-Interaktion mit Tool-Calling-Loop durch.

        Args:
            messages: Liste der Chat-Nachrichten.
            system_prompt: Optionaler System-Prompt.

        Returns:
            str: Die finale Antwort des Agenten.
        """
        all_messages = []
        if system_prompt:
            all_messages.append({'role': 'system', 'content': system_prompt})
        all_messages.extend(messages)

        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.chat(
                model=self.model,
                messages=all_messages,
                tools=self.tools_definition
            )

            message = response.get('message', {})
            all_messages.append(message)

            if not message.get('tool_calls'):
                return message.get('content', "")

            # Verarbeite Tool-Calls
            for tool_call in message['tool_calls']:
                function_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})

                logger.info(f"Agent ruft Tool auf: {function_name} mit {args}")

                if function_name in self.available_tools:
                    try:
                        tool_result = self.available_tools[function_name](**args)
                    except Exception as e:
                        tool_result = f"Fehler bei Tool-Ausführung: {e}"
                else:
                    tool_result = f"Tool {function_name} nicht verfügbar."

                all_messages.append({
                    'role': 'tool',
                    'content': str(tool_result),
                    'tool_call_id': tool_call.get('id') # Ollama supports this if present
                })

        return "Fehler: Maximale Anzahl an Iterationen erreicht."
