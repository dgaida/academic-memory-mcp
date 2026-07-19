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
    """Agent, der Tool-Calling mittels Ollama unterstützt und optional Cloud-LLMs mit Anonymisierung nutzt."""

    def __init__(self, model: str = None, base_url: str = None, use_cloud: bool = False,
                 cloud_provider: str = "openai", cloud_model: str = "gpt-4o", api_key: str = None) -> None:
        """Initialisiert den Agenten.

        Args:
            model (str, optional): Name des lokalen Ollama-Modells. Defaults to None.
            base_url (str, optional): Basis-URL des Ollama-Servers. Defaults to None.
            use_cloud (bool): Ob ein Cloud-LLM genutzt werden soll. Defaults to False.
            cloud_provider (str): Name des Cloud-Providers. Defaults to "openai".
            cloud_model (str): Name des Cloud-Modells. Defaults to "gpt-4o".
            api_key (str, optional): API-Key für den Cloud-Provider. Defaults to None.
        """
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
        self.last_tool_error = None

        self.available_tools: Dict[str, Callable] = {
            "read_file": self._tool_read_file,
            "search_documents": self._tool_search_documents,
            "get_student_info": self._tool_get_student_info,
            "get_appointment_slots": self._tool_get_appointment_slots,
            "manage_calendar_appointment": self._tool_manage_calendar_appointment,
            "save_email_attachments": self._tool_save_email_attachments,
            "create_colloquium_config": self._tool_create_colloquium_config,
            "update_colloquium_config": self._tool_update_colloquium_config
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
                    "description": "Prüft die Verfügbarkeit eines Slots (Standard: 30 Min) und trägt bei Erfolg einen Kalendertermin (Europe/Berlin) ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {
                                "type": "string",
                                "description": "Beginn des Termins ('YYYY-MM-DD HH:MM')."
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Ende des Termins ('YYYY-MM-DD HH:MM')."
                            },
                            "subject": {
                                "type": "string",
                                "description": "Betreff des Kalendereintrags."
                            },
                            "student_email": {
                                "type": "string",
                                "description": "E-Mail-Adresse des Studenten."
                            },
                            "original_mail_date": {
                                "type": "string",
                                "description": "Datum der studentischen Mail im Format DD.MM.YY."
                            },
                            "is_colloquium": {
                                "type": "boolean",
                                "description": "Ob es sich um ein Kolloquium handelt (Dauer 60 Min, Update config.json)."
                            }
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            }
       ,
            {
                "type": "function",
                "function": {
                    "name": "create_colloquium_config",
                    "description": "Erstellt eine config.json für den colloquium-protocol-creator bei finaler Abgabe. Falls die Datei bereits existiert, wird nur der Dateiname der Bachelorarbeit aktualisiert.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_path": {
                                "type": "string",
                                "description": "Pfad zur E-Mail-Datei."
                            },
                            "pdf_filename": {
                                "type": "string",
                                "description": "Dateiname der PDF-Arbeit im Anhang."
                            }
                        },
                        "required": ["email_path", "pdf_filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_colloquium_config",
                    "description": "Aktualisiert Datum und Uhrzeit in der config.json eines Studenten. Falls die config.json noch nicht existiert, wird sie mit Standardwerten erstellt.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_email": {
                                "type": "string",
                                "description": "E-Mail-Adresse des Studenten."
                            },
                            "date": {
                                "type": "string",
                                "description": "Datum des Kolloquiums (DD.MM.YYYY)."
                            },
                            "time": {
                                "type": "string",
                                "description": "Uhrzeit des Kolloquiums (hh:mm)."
                            }
                        },
                        "required": ["student_email", "date", "time"]
                    }
                }
            }
        ]

    def _tool_read_file(self, path: str) -> str:
        """Liest eine Datei ein.

        Args:
            path (str): Der Pfad zur Datei.

        Returns:
            str: Dateiinhalt oder Fehlermeldung.
        """
        p = Path(path)
        if not p.exists():
            return f"Fehler: Datei {path} nicht gefunden."
        content = self.parser_factory.parse(p)
        return content or "Fehler: Datei konnte nicht gelesen werden oder ist leer."

    def _tool_search_documents(self, query: str) -> str:
        """Sucht im Index nach Informationen.

        Args:
            query (str): Die Suchanfrage.

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
        """Holt Studentendaten aus dem MetadataStore.

        Args:
            student_name (str): Name oder Teilname des Studenten.

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
        """Liest die aktuell verfügbaren freien Terminslots ein.

        Returns:
            str: Freie Slots als Markdown oder Fehlermeldung.
        """
        slots_config_path = self.cfg.calendar.appointment_slots_path
        path = Path(slots_config_path)
        if not path.is_absolute():
            path = self.cfg.config_dir.parent / path

        if not path.exists():
            return f"Fehler: Die Datei mit freien Slots wurde unter {path.as_posix()} nicht gefunden. Das Makro Freeslotexport.bas muss eventuell zuerst ausgeführt werden."
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Fehler beim Lesen der freien Slots: {e}"

    def _tool_manage_calendar_appointment(self, start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: str = None, body: str = None, is_colloquium: bool = False) -> str:
        """Prüft die Verfügbarkeit eines Slots und trägt bei Erfolg einen Kalendertermin ein.

        Args:
            start_time (str): Beginn des Termins ('YYYY-MM-DD HH:MM').
            end_time (str): Ende des Termins ('YYYY-MM-DD HH:MM').
            subject (str): Betreff des Kalendereintrags.
            student_email (str): E-Mail-Adresse des Studenten.
            original_mail_date (str, optional): Datum der studentischen Mail (DD.MM.YY). Defaults to None.
            body (str, optional): Der Inhalt der E-Mail für den Kalendereintrag. Defaults to None.
            is_colloquium (bool): Gibt an, ob es sich um ein Kolloquium handelt. Defaults to False.

        Returns:
            str: Erfolgs- oder Fehlermeldung.
        """
        try:
            import win32com.client
        except ImportError:
            return "Fehler: pywin32 ist nicht installiert. Kalender-Funktionen sind nicht verfügbar."

        try:
            # Slot prüfen - Nutze Europe/Berlin Zeitzone
            tz = ZoneInfo("Europe/Berlin")
            dt_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            if dt_start < datetime.now(tz):
                return "Fehler: Der Termin liegt in der Vergangenheit und wird daher nicht angelegt."

            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")

            target_account = get_config().user.email
            target_calendar_name = "Kalender (Nur dieser Computer)"

            # Kalender suchen
            cal_folder = None
            for i in range(1, namespace.Accounts.Count + 1):
                account = namespace.Accounts.Item(i)
                if account.SmtpAddress.lower() == target_account.lower():
                    logger.info(f"ERFOLG: Konto gefunden: {account.SmtpAddress}")
                    store = account.DeliveryStore
                    root = store.GetRootFolder()
                    for j in range(1, root.Folders.Count + 1):
                        folder = root.Folders.Item(j)
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

            if not cal_folder:
                logger.error(f"Kein Kalender gefunden für {target_account}")
            else:
                logger.info(f"Nutze Kalender: {cal_folder.Name} (Pfad: {cal_folder.FolderPath})")

            if target_folder:
                logger.info(f"ERFOLG: Zielordner für Entwürfe gefunden: {target_folder.FolderPath}")
            else:
                logger.warning(f"Zielordner {target_folder_name} nicht gefunden.")

            # Slot prüfen - Nutze Europe/Berlin Zeitzone
            dt_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M").replace(tzinfo=tz)

            # Logik: Kolloquium immer 60 Min
            if is_colloquium:
                if (dt_end - dt_start) < timedelta(minutes=60):
                    logger.info("Kolloquium erkannt, setze Dauer auf 60 Minuten.")
                    dt_end = dt_start + timedelta(minutes=60)

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
            auto_send = self.cfg.calendar.send_invitations_automatically

            if dt_end <= dt_start:
                return f"Fehler: Das Ende des Termins ({end_time}) muss nach dem Beginn ({start_time}) liegen."

            if not auto_send and target_folder:
                appointment = target_folder.Items.Add(1) # 1 = olAppointmentItem
                logger.info(f"ERFOLG: Erstelle Termin-Entwurf in '{target_folder_name}' ({target_folder.FolderPath}).")
            else:
                appointment = cal_folder.Items.Add(1) # 1 = olAppointmentItem
                if not auto_send:
                    logger.warning(f"Zielordner '{target_folder_name}' nicht gefunden. Erstelle im Standard-Kalender.")

            appointment.Subject = subject
            appointment.Start = dt_start.replace(tzinfo=None)
            appointment.End = dt_end.replace(tzinfo=None)
            appointment.Location = "Zoom (siehe E-Mail-Signatur)"
            body_text = body if body else (f"Terminbestätigung auf Basis Ihrer Mail vom {original_mail_date}" if original_mail_date else "Terminbestätigung via MCP University System.")
            appointment.Body = body_text

            # Einladung vorbereiten
            recipient = appointment.Recipients.Add(student_email)
            recipient.Type = 1 # 1 = olTo
            appointment.MeetingStatus = 1 # 1 = olMeeting

            appointment.Save()

            # Automatisches Update der Kolloquium-Config falls erkannt
            if is_colloquium:
                try:
                    self._tool_update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))
                except Exception as e:
                    logger.error(f"Fehler beim automatischen Update der Kolloquium-Config: {e}")

            if auto_send:
                appointment.Send()
                return f"ERFOLG: Termin '{subject}' am {start_time} wurde eingetragen und Einladung an {student_email} gesendet."
            else:
                msg = f"ERFOLG: Termin-Entwurf '{subject}' am {start_time} wurde in '{target_folder_name if target_folder else cal_folder.Name}' gespeichert (nicht gesendet)."
                logger.info(msg)
                return msg

        except Exception as e:
            return f"Fehler bei der Kalender-Verarbeitung: {e}"



    def _tool_create_colloquium_config(self, email_path: str, pdf_filename: str) -> str:
        """Erstellt eine config.json für den colloquium-protocol-creator bei finaler Abgabe.
        Falls die Datei bereits existiert, wird nur der Dateiname der Bachelorarbeit aktualisiert.
        """
        try:
            import json
            p = Path(email_path)
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

    def _tool_update_colloquium_config(self, student_email: str, date: str, time: str) -> str:
        """Aktualisiert Datum und Uhrzeit in der config.json eines Studenten.
        Falls die config.json noch nicht existiert, wird sie mit Standardwerten erstellt.
        """
        try:
            import json
            from ..metadata.store import MetadataStore
            store = MetadataStore(self.cfg.sqlite_path)
            
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

                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
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

    def _tool_save_email_attachments(self, email_path: str) -> str:
        """Extrahiert Anhänge aus der E-Mail und speichert sie im Elternordner des E-Mail-Ordners.

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

            # Elternordner des Ordners, in dem die E-Mail liegt
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

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None,
             sender_name: str = None, sender_email: str = None) -> str:
        """Führt eine Chat-Interaktion mit Tool-Calling-Loop durch, optional mit Anonymisierung.

        Args:
            messages (List[Dict[str, str]]): Liste der Chat-Nachrichten.
            system_prompt (str, optional): Optionaler System-Prompt. Defaults to None.
            sender_name (str, optional): Name des Absenders für Anonymisierung. Defaults to None.
            sender_email (str, optional): E-Mail des Absenders für Anonymisierung. Defaults to None.

        Returns:
            str: Die finale Antwort des Agenten.
        """
        self.last_appointment_info = None
        self.last_tool_error = None

        processed_messages = []
        if self.use_cloud and self.anonymizer and sender_name and sender_email:
            # Anonymisiere alle User-Nachrichten
            for msg in messages:
                if msg['role'] == 'user':
                    anon_content = self.anonymizer.anonymize(msg['content'], sender_name, sender_email)
                    processed_messages.append({'role': 'user', 'content': anon_content})
                else:
                    processed_messages.append(msg)

            # Anonymisiere System Prompt falls vorhanden
            if system_prompt:
                system_prompt = self.anonymizer.anonymize(system_prompt, sender_name, sender_email)
        else:
            processed_messages = messages

        all_messages = []
        if system_prompt:
            all_messages.append({'role': 'system', 'content': system_prompt})
        all_messages.extend(processed_messages)

        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.chat(
                messages=all_messages,
                tools=self.tools_definition
            )

            message = response.get('message', {})

            # Falls Cloud, de-anonymisieren wir das Ergebnis für den internen Gebrauch
            if self.use_cloud and self.anonymizer:
                if message.get('content'):
                    message['content'] = self.anonymizer.deanonymize_text(message['content'])
                if message.get('tool_calls'):
                    for tc in message['tool_calls']:
                        tc['function']['arguments'] = self.anonymizer.deanonymize_args(tc['function'].get('arguments', {}))

            all_messages.append(message)

            if not message.get('tool_calls'):
                final_content = message.get('content', "")
                logger.info(f"Agent finale Antwort: {final_content}")
                return final_content

            # Verarbeite Tool-Calls
            for tool_call in message['tool_calls']:
                function_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})

                logger.info(f"Agent ruft Tool auf: {function_name} mit {args}")

                if function_name in self.available_tools:
                    try:
                        tool_result = self.available_tools[function_name](**args)
                        if function_name == "manage_calendar_appointment" and "ERFOLG" in str(tool_result):
                            self.last_appointment_info = args
                    except TypeError as e:
                        tool_result = f"Fehler: Falsche Argumente für Tool '{function_name}'. Details: {e}. Bitte stelle sicher, dass ALLE erforderlichen Argumente korrekt übergeben werden."
                        logger.error(f"Tool-Argument-Fehler: {e}")
                        self.last_tool_error = tool_result
                    except Exception as e:
                        tool_result = f"Fehler bei Tool-Ausführung: {e}"
                        logger.error(f"Tool-Ausführungs-Fehler: {e}")
                        self.last_tool_error = tool_result
                else:
                    tool_result = f"Tool {function_name} nicht verfügbar."

                logger.info(f"Tool Ergebnis: {tool_result}")

                # Falls Cloud, anonymisiere das Tool-Ergebnis bevor es zurück geht
                if self.use_cloud and self.anonymizer:
                    for placeholder, original in self.anonymizer.mapping.items():
                        tool_result = str(tool_result).replace(original, placeholder)

                all_messages.append({
                    'role': 'tool',
                    'content': str(tool_result),
                    'tool_call_id': tool_call.get('id')
                })

        return "Fehler: Maximale Anzahl an Iterationen erreicht."
