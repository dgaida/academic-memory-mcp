import re
from pathlib import Path

# 1. Update tool_server.py
server_path = Path("mcp_university/mcp_server/tool_server.py")
server_content = server_path.read_text(encoding="utf-8")

# Update manage_calendar_appointment signature and logic in tool_server.py
server_content = server_content.replace(
    'def manage_calendar_appointment(start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: Optional[str] = None, body: Optional[str] = None) -> str:',
    'def manage_calendar_appointment(start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: Optional[str] = None, body: Optional[str] = None, is_colloquium: bool = False) -> str:'
)

server_content = server_content.replace(
    'if "kolloquium" in subject.lower():',
    'if is_colloquium:'
)

# 2. Update engine.py
engine_path = Path("mcp_university/agent/engine.py")
engine_content = engine_path.read_text(encoding="utf-8")

# Update manage_calendar_appointment signature and logic in engine.py
engine_content = engine_content.replace(
    'def _tool_manage_calendar_appointment(self, start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: str = None, body: str = None) -> str:',
    'def _tool_manage_calendar_appointment(self, start_time: str, end_time: str, subject: str, student_email: str, original_mail_date: str = None, body: str = None, is_colloquium: bool = False) -> str:'
)

# Replace the duration logic
engine_content = engine_content.replace(
    'if "kolloquium" in subject.lower():',
    'if is_colloquium:'
)

# Replace the automatic update logic
engine_content = engine_content.replace(
    'if "kolloquium" in subject.lower():',
    'if is_colloquium:'
)

# Update the tools_definition for manage_calendar_appointment
tools_def_pattern = r'("name": "manage_calendar_appointment",.*?)"original_mail_date": \{.*?\}(.*?\})'
replacement = r'\1"original_mail_date": {"type": "string", "description": "Datum der studentischen Mail im Format DD.MM.YY."},\n                            "is_colloquium": {"type": "boolean", "description": "Ob es sich um ein Kolloquium handelt (Dauer 60 Min, Update config.json)."}\2'
# engine_content = re.sub(tools_def_pattern, replacement, engine_content, flags=re.DOTALL)

# Writing back
server_path.write_text(server_content, encoding="utf-8")
engine_path.write_text(engine_content, encoding="utf-8")
