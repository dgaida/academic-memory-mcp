import sys
from pathlib import Path

path = "mcp_university/agent/engine.py"
content = Path(path).read_text(encoding="utf-8")

old_fragment = '''                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    config_path = Path(row[0]).parent / "config.json"'''

new_fragment = '''                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    potential_path = Path(row[0]).parent / "config.json"
                    if potential_path.exists() or Path(row[0]).name in ["SentItems", "Inbox", "Posteingang", "Gesendete Elemente"]:
                         config_path = potential_path'''

if old_fragment in content:
    content = content.replace(old_fragment, new_fragment)
    Path(path).write_text(content, encoding="utf-8")
    print(f"Fixed {path}")
else:
    print(f"Fragment not found in {path}")
