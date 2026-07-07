from pathlib import Path
path = Path("mcp_university/mcp_server/tool_server.py")
content = path.read_text(encoding="utf-8")

old_block = r'''            # (id, name, email, topic, status, folder_path)
            res = f"Student: {student[1]}
Email: {student[2]}
Thema: {student[3]}
Status: {student[4]}
Ordner: {student[5]}
"'''

new_block = r'''            # (id, name, email, topic, status, folder_path)
            res = (f"Student: {student[1]}\n"
                   f"Email: {student[2]}\n"
                   f"Thema: {student[3]}\n"
                   f"Status: {student[4]}\n"
                   f"Ordner: {student[5]}\n")'''

if old_block in content:
    content = content.replace(old_block, new_block)

path.write_text(content, encoding="utf-8")
