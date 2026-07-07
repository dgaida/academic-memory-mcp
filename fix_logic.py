import sys
from pathlib import Path

def fix_file(path):
    content = Path(path).read_text(encoding="utf-8")

    old_fragment = '''                # Die config.json liegt im Hauptordner des Studenten, nicht in Unterordnern
                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    # Fallback: Falls row[0] ein Unterordner wie "SentItems" ist
                    config_path = Path(row[0]).parent / "config.json"'''

    new_fragment = '''                # Die config.json liegt im Hauptordner des Studenten, nicht in Unterordnern
                config_path = Path(row[0]) / "config.json"
                if not config_path.exists():
                    # Fallback: Falls row[0] ein Unterordner wie "SentItems" ist
                    potential_path = Path(row[0]).parent / "config.json"
                    if potential_path.exists() or Path(row[0]).name in ["SentItems", "Inbox", "Posteingang", "Gesendete Elemente"]:
                         config_path = potential_path'''

    if old_fragment in content:
        content = content.replace(old_fragment, new_fragment)
        Path(path).write_text(content, encoding="utf-8")
        print(f"Fixed {path}")
    else:
        print(f"Fragment not found in {path}")

fix_file("mcp_university/mcp_server/tool_server.py")
fix_file("mcp_university/agent/engine.py")
