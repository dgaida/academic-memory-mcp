from pathlib import Path
path = Path("mcp_university/mcp_server/tool_server.py")
content = path.read_text(encoding="utf-8")

old_block = r'''                if row:
                    res += f"
Zusammenfassung des Ordners:
{row[0]}"'''

new_block = r'''                if row:
                    res += f"\nZusammenfassung des Ordners:\n{row[0]}"'''

content = content.replace(old_block, new_block)

path.write_text(content, encoding="utf-8")
