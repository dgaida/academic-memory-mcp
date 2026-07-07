from pathlib import Path
path = Path("mcp_university/mcp_server/tool_server.py")
content = path.read_text(encoding="utf-8")

# Find the end of create_colloquium_config
marker = 'return f"ERFOLG: Konfiguration erstellt/aktualisiert unter {config_path}"\n        except Exception as e:\n            return f"Fehler beim Erstellen der Konfiguration: {e}"'
idx = content.find(marker)
if idx != -1:
    content = content[:idx + len(marker)] + "\n\n"

# Now append update_colloquium_config and the rest
update_tool = r'''    @mcp.tool
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
'''

content += update_tool
path.write_text(content, encoding="utf-8")
