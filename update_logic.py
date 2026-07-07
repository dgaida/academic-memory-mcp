import sys
from pathlib import Path

path = Path("mcp_university/agent/engine.py")
content = path.read_text(encoding="utf-8")

# Update manage_calendar_appointment to call _tool_update_colloquium_config based on is_colloquium
content = content.replace(
    'appointment.Save()',
    'appointment.Save()\n\n            # Automatisches Update der Kolloquium-Config falls erkannt\n            if is_colloquium:\n                try:\n                    self._tool_update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))\n                except Exception as e:\n                    logger.error(f"Fehler beim automatischen Update der Kolloquium-Config: {e}")'
)

path.write_text(content, encoding="utf-8")

# Also update tool_server.py
server_path = Path("mcp_university/mcp_server/tool_server.py")
server_content = server_path.read_text(encoding="utf-8")

server_content = server_content.replace(
    'appointment.Save()',
    'appointment.Save()\n\n            # Automatisches Update der Kolloquium-Config falls erkannt\n            if is_colloquium:\n                try:\n                    update_colloquium_config(student_email, dt_start.strftime("%d.%m.%Y"), dt_start.strftime("%H:%M"))\n                except Exception as e:\n                    logger.error(f"Fehler beim automatischen Update der Kolloquium-Config: {e}")'
)

server_path.write_text(server_content, encoding="utf-8")
