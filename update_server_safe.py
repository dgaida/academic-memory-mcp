import sys
import json
from pathlib import Path

path = Path("mcp_university/mcp_server/tool_server.py")
lines = path.read_text(encoding="utf-8").splitlines()

new_lines = []
skip = False

# This is a bit tedious but safer than regex on huge strings with nested quotes
for line in lines:
    if 'def manage_calendar_appointment(' in line:
        line = line.replace('body: Optional[str] = None) -> str:', 'body: Optional[str] = None, is_colloquium: bool = False) -> str:')

    if 'if "kolloquium" in subject.lower():' in line:
        line = line.replace('if "kolloquium" in subject.lower():', 'if is_colloquium:')

    if 'update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))' in line:
         # ensure it's wrapped in is_colloquium
         pass # will handle in a better way if needed

    new_lines.append(line)

# Re-apply create_colloquium_config
content = "\n".join(new_lines)

# Manually replace the two tools with their final versions
create_old = """    @mcp.tool
    def create_colloquium_config(email_path: str, pdf_filename: str) -> str:
        \"\"\"Erstellt eine config.json für den colloquium-protocol-creator bei finaler Abgabe.

        Args:
            email_path: Pfad zur E-Mail.
            pdf_filename: Dateiname der PDF-Arbeit im Anhang.

        Returns:
            Erfolgsmeldung oder Fehler.
        \"\"\"
        try:
            import json
            p = Path(email_path)
            # Anhänge liegen im Elternordner des E-Mail-Ordners (p.parent.parent)
            target_dir = p.parent.parent
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)

            config_path = target_dir / "config.json"

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

            return f"ERFOLG: Konfiguration erstellt unter {config_path}"
        except Exception as e:
            return f"Fehler beim Erstellen der Konfiguration: {e}\""""

create_new = """    @mcp.tool
    def create_colloquium_config(email_path: str, pdf_filename: str) -> str:
        \"\"\"Erstellt eine config.json für den colloquium-protocol-creator bei finaler Abgabe.
        Falls die Datei bereits existiert, wird nur der Dateiname der Bachelorarbeit aktualisiert.

        Args:
            email_path: Pfad zur E-Mail.
            pdf_filename: Dateiname der PDF-Arbeit im Anhang.

        Returns:
            Erfolgsmeldung oder Fehler.
        \"\"\"
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
            return f"Fehler beim Erstellen der Konfiguration: {e}\""""

update_old = """    @mcp.tool
    def update_colloquium_config(student_email: str, date: str, time: str) -> str:
        \"\"\"Aktualisiert Datum und Uhrzeit in der config.json eines Studenten.

        Args:
            student_email: E-Mail-Adresse des Studenten.
            date: Datum des Kolloquiums (DD.MM.YYYY).
            time: Uhrzeit des Kolloquiums (hh:mm).

        Returns:
            Erfolgsmeldung oder Fehler.
        \"\"\"
        try:
            import json
            with store._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    SELECT f.path FROM students s
                    JOIN folders f ON s.folder_id = f.id
                    WHERE s.email = ?
                \"\"\", (student_email,))
                row = cursor.fetchone()
                if not row:
                    return f"Fehler: Kein Ordner für Student {student_email} in Datenbank gefunden."

                # student_folder = Path(row[0])
                # Die config.json liegt im Hauptordner des Studenten, nicht in Unterordnern
                # Wir suchen sie im gefundenen Pfad und ggf. darüber
                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    # Fallback: Falls row[0] ein Unterordner wie "SentItems" ist
                    config_path = Path(row[0]).parent / "config.json"

                if not config_path.exists():
                     return f"Fehler: config.json nicht gefunden in {Path(row[0])}"

                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                data["colloquium"]["date"] = date
                data["colloquium"]["time"] = time

                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return f"ERFOLG: Kolloquiumstermin in {config_path} aktualisiert."
        except Exception as e:
            return f"Fehler beim Aktualisieren der Konfiguration: {e}\""""

update_new = """    @mcp.tool
    def update_colloquium_config(student_email: str, date: str, time: str) -> str:
        \"\"\"Aktualisiert Datum und Uhrzeit in der config.json eines Studenten.
        Falls die config.json noch nicht existiert, wird sie mit Standardwerten erstellt.

        Args:
            student_email: E-Mail-Adresse des Studenten.
            date: Datum des Kolloquiums (DD.MM.YYYY).
            time: Uhrzeit des Kolloquiums (hh:mm).

        Returns:
            Erfolgsmeldung oder Fehler.
        \"\"\"
        try:
            import json
            with store._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    SELECT f.path FROM students s
                    JOIN folders f ON s.folder_id = f.id
                    WHERE s.email = ?
                \"\"\", (student_email,))
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
            return f"Fehler beim Aktualisieren der Konfiguration: {e}\""""

content = content.replace(create_old, create_new)
content = content.replace(update_old, update_new)

# Add logic for automatic update inside manage_calendar_appointment
content = content.replace(
    'appointment.Save()',
    'appointment.Save()\\n\\n            # Automatisches Update der Kolloquium-Config falls erkannt\\n            if is_colloquium:\\n                try:\\n                    update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))\\n                except Exception as e:\\n                    logger.error(f"Fehler beim automatischen Update der Kolloquium-Config: {e}")'
)

path.write_text(content.replace('\\n', '\n'), encoding="utf-8")
