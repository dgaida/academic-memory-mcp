import sys
import re
from pathlib import Path

path = Path("mcp_university/mcp_server/tool_server.py")
content = path.read_text(encoding="utf-8")

new_create = r'''    @mcp.tool
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
            return f"Fehler beim Erstellen der Konfiguration: {e}"'''

new_update = r'''    @mcp.tool
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
            return f"Fehler beim Aktualisieren der Konfiguration: {e}"'''

# Use simple string replacement for create_colloquium_config
old_create_start = '    @mcp.tool\n    def create_colloquium_config(email_path: str, pdf_filename: str) -> str:'
old_create_end = 'return f"ERFOLG: Konfiguration erstellt unter {config_path}"\n        except Exception as e:\n            return f"Fehler beim Erstellen der Konfiguration: {e}"'

# Find the block
start_idx = content.find(old_create_start)
end_idx = content.find(old_create_end) + len(old_create_end)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_create + content[end_idx:]

# Use simple string replacement for update_colloquium_config
old_update_start = '    @mcp.tool\n    def update_colloquium_config(student_email: str, date: str, time: str) -> str:'
old_update_end = 'return f"ERFOLG: Kolloquiumstermin in {config_path} aktualisiert."\n        except Exception as e:\n            return f"Fehler beim Aktualisieren der Konfiguration: {e}"'

start_idx = content.find(old_update_start)
end_idx = content.find(old_update_end) + len(old_update_end)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_update + content[end_idx:]

path.write_text(content, encoding="utf-8")
