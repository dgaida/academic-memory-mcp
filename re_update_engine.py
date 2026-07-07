import sys
import re
from pathlib import Path

path = Path("mcp_university/agent/engine.py")
content = path.read_text(encoding="utf-8")

# 1. Add tools to available_tools if not present
if '"create_colloquium_config": self._tool_create_colloquium_config' not in content:
    content = content.replace(
        '"save_email_attachments": self._tool_save_email_attachments',
        '"save_email_attachments": self._tool_save_email_attachments,\n            "create_colloquium_config": self._tool_create_colloquium_config,\n            "update_colloquium_config": self._tool_update_colloquium_config'
    )

# 2. Add tools to tools_definition if not present
if '"name": "create_colloquium_config"' not in content:
    tools_def_extension = r''',
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
            }'''
    content = re.sub(r'(\s+"name": "manage_calendar_appointment",.*?\}\s+)\s+\]', r'\1' + tools_def_extension + '\n        ]', content, flags=re.DOTALL)

# 3. Add tool implementations if not present
if 'def _tool_create_colloquium_config' not in content:
    new_tool_implementations = r'''
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
                    config_path = Path(row[0]).parent / "config.json"

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
'''
    content = content.replace('    def _tool_save_email_attachments(self, email_path: str) -> str:', new_tool_implementations + '\n    def _tool_save_email_attachments(self, email_path: str) -> str:')

path.write_text(content, encoding="utf-8")
