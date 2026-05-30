"""Engine-Modul für den Agenten."""
import logging
from typing import List, Dict, Callable
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import get_config
from ..parser.factory import ParserFactory
from ..retrieval.index import SearchIndex
from ..metadata.store import MetadataStore
from ..utils.llm_client_wrapper import LLMClientWrapper
from ..utils.anonymizer import Anonymizer

logger = logging.getLogger(__name__)

class Agent:
    """Agent, der Tool-Calling unterstützt und optional Cloud-LLMs mit Anonymisierung nutzt."""

    def __init__(self, model: str = None, base_url: str = None, use_cloud: bool = False,
                 cloud_provider: str = "openai", cloud_model: str = "gpt-4o", api_key: str = None):
        """Initialisiert den Agenten."""
        self.cfg = get_config()
        self.model = model or self.cfg.llm.model
        self.base_url = str(base_url or self.cfg.llm.base_url)

        self.use_cloud = use_cloud
        if self.use_cloud:
            self.client = LLMClientWrapper(provider=cloud_provider, model=cloud_model, api_key=api_key)
            self.anonymizer = Anonymizer(model=self.model, base_url=self.base_url)
        else:
            self.client = LLMClientWrapper(provider="ollama", model=self.model, base_url=self.base_url)
            self.anonymizer = None

        self.parser_factory = ParserFactory(self.cfg.data_dir / "cache")
        self.store = MetadataStore(self.cfg.sqlite_path)
        self.index = SearchIndex(str(self.cfg.qdrant_path), self.cfg.embeddings.model, store=self.store)
        self.last_appointment_info = None

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
                            "path": {"type": "string", "description": "Der Pfad zur Datei."}
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
                            "query": {"type": "string", "description": "Die Suchanfrage."}
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
                            "student_name": {"type": "string", "description": "Name oder Teilname des Studenten."}
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
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_calendar_appointment",
                    "description": "Prüft die Verfügbarkeit eines Slots und trägt einen Kalendertermin ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string", "description": "Beginn (YYYY-MM-DD HH:MM)."},
                            "end_time": {"type": "string", "description": "Ende (YYYY-MM-DD HH:MM)."},
                            "subject": {"type": "string", "description": "Betreff."},
                            "student_email": {"type": "string", "description": "E-Mail-Adresse."},
                            "original_mail_date": {"type": "string", "description": "Datum der studentischen Mail (DD.MM.YY)."}
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            }
        ]

    def _tool_read_file(self, path: str) -> str:
        """Reads a file content."""
        p = Path(path)
        if not p.exists():
            return f"Fehler: Datei {path} nicht gefunden."
        content = self.parser_factory.parse(p)
        return content or "Fehler: Datei konnte nicht gelesen werden oder ist leer."

    def _tool_search_documents(self, query: str) -> str:
        """Searches documents."""
        results = self.index.search(query, top_k=3)
        if not results:
            return "Keine relevanten Dokumente gefunden."
        output = ""
        for res in results:
            output += f"--- {res['filename']} (Score: {res['score']:.2f}) ---\n{res['content']}\n\n"
        return output

    def _tool_get_student_info(self, student_name: str) -> str:
        """Gets student info."""
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
            return f"Student: {student[1]}\nEmail: {student[2]}\nThema: {student[3]}\nStatus: {student[4]}\nOrdner: {student[6]}\n"

    def _tool_get_appointment_slots(self) -> str:
        """Gets appointment slots."""
        path = Path(r"D:\TH_Koeln\academic-memory-mcp\data\free_slots.md")
        if not path.exists():
            return "Fehler: Die Datei mit freien Slots wurde nicht gefunden."
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Fehler beim Lesen der freien Slots: {e}"

    def _tool_manage_calendar_appointment(self, start_time: str, end_time: str, subject: str,
                                         student_email: str, original_mail_date: str = None) -> str:
        """Manages calendar appointment."""
        try:
            import win32com.client
        except ImportError:
            return "Fehler: pywin32 nicht installiert."

        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            target_account = "daniel.gaida@th-koeln.de"
            target_calendar_name = "Kalender (Nur dieser Computer)"

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
                        try:
                            cal_folder = store.GetDefaultFolder(9)
                        except Exception:
                            pass
                    break

            if not cal_folder:
                return "Fehler: Kalender nicht gefunden."

            tz = ZoneInfo("Europe/Berlin")
            dt_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            dt_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)

            if "kolloquium" in subject.lower() and (dt_end - dt_start) < timedelta(minutes=60):
                dt_end = dt_start + timedelta(minutes=60)

            appointment = cal_folder.Items.Add(1)
            appointment.Subject = subject
            appointment.Start = dt_start
            appointment.End = dt_end
            appointment.Location = "Zoom"
            appointment.Body = f"Terminbestätigung auf Basis Ihrer Mail vom {original_mail_date}" if original_mail_date else "Terminbestätigung."

            rec = appointment.Recipients.Add(student_email)
            rec.Type = 1
            appointment.MeetingStatus = 1
            appointment.Save()

            return f"ERFOLG: Termin '{subject}' am {start_time} wurde eingetragen."
        except Exception as e:
            return f"Fehler bei der Kalender-Verarbeitung: {e}"

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None,
             sender_name: str = None, sender_email: str = None) -> str:
        """Führt eine Chat-Interaktion durch, optional mit Anonymisierung."""
        self.last_appointment_info = None

        processed_messages = []
        if self.use_cloud and self.anonymizer and sender_name and sender_email:
            for msg in messages:
                if msg['role'] == 'user':
                    anon_content = self.anonymizer.anonymize(msg['content'], sender_name, sender_email)
                    processed_messages.append({'role': 'user', 'content': anon_content})
                else:
                    processed_messages.append(msg)

            if system_prompt:
                system_prompt = self.anonymizer.anonymize(system_prompt, sender_name, sender_email)
        else:
            processed_messages = messages

        all_messages = processed_messages.copy()

        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.chat(
                messages=all_messages,
                system_prompt=system_prompt,
                tools=self.tools_definition
            )

            message = response.get('message', {})
            if self.use_cloud and self.anonymizer:
                if message.get('content'):
                    message['content'] = self.anonymizer.deanonymize_text(message['content'])
                if message.get('tool_calls'):
                    for tc in message['tool_calls']:
                        tc['function']['arguments'] = self.anonymizer.deanonymize_args(tc['function'].get('arguments', {}))

            all_messages.append(message)

            if not message.get('tool_calls'):
                return message.get('content', "")

            for tool_call in message['tool_calls']:
                fn_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})

                if fn_name in self.available_tools:
                    try:
                        res = self.available_tools[fn_name](**args)
                        if fn_name == "manage_calendar_appointment" and "ERFOLG" in str(res):
                            self.last_appointment_info = args
                    except Exception as e:
                        res = f"Fehler: {e}"
                else:
                    res = "Tool nicht gefunden."

                if self.use_cloud and self.anonymizer:
                    for placeholder, original in self.anonymizer.mapping.items():
                        res = str(res).replace(original, placeholder)

                all_messages.append({
                    'role': 'tool',
                    'content': str(res),
                    'tool_call_id': tool_call.get('id')
                })

        return "Fehler: Maximale Iterationen erreicht."
