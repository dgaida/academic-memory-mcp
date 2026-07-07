import sys
from pathlib import Path

path = Path("mcp_university/agent/engine.py")
content = path.read_text(encoding="utf-8")

new_props = '''                            "original_mail_date": {
                                "type": "string",
                                "description": "Datum der studentischen Mail im Format DD.MM.YY."
                            },
                            "is_colloquium": {
                                "type": "boolean",
                                "description": "Ob es sich um ein Kolloquium handelt (Dauer 60 Min, Update config.json)."
                            }'''

content = content.replace(
    '''                            "original_mail_date": {
                                "type": "string",
                                "description": "Datum der studentischen Mail im Format DD.MM.YY."
                            }''',
    new_props
)

path.write_text(content, encoding="utf-8")
