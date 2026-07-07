from pathlib import Path
path = Path("mcp_university/mcp_server/tool_server.py")
content = path.read_text(encoding="utf-8")

import re
old_block = r'''        output = ""
        for res in results:
            output += f"--- {res['filename']} (Relevanz: {res['score']:.2f}) ---
{res['content']}

"
        return output'''

new_block = r'''        output = ""
        for res in results:
            output += f"--- {res['filename']} (Relevanz: {res['score']:.2f}) ---\n{res['content']}\n\n"
        return output'''

if old_block in content:
    content = content.replace(old_block, new_block)
else:
    # Try another variation if sed messed it up differently
    pattern = r'output \+= f"--- \{res\[\?.\?filename.\?\]\} \(Relevanz: \{res\[\?.\?score.\?\]\}:.2f\) ---\s+\{res\[\?.\?content.\?\]\}\s+"'
    content = re.sub(pattern, new_block, content, flags=re.DOTALL)

path.write_text(content, encoding="utf-8")
