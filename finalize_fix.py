import re
from pathlib import Path

def fix_file(path, content):
    # Remove unused imports in profiler
    if path.name == "profiler.py":
        content = content.replace("from typing import List, Dict, Any, Optional, Tuple", "from typing import List, Dict, Any, Optional")

    # Remove unused imports in scripts
    if path.name == "create_person_profiles.py":
        content = content.replace("import sys", "")

    # Fix process_sorted_emails.py
    if path.name == "process_sorted_emails.py":
        # Remove duplicate skill_path blocks
        # We want to keep ONLY one block before Gender Determination
        pattern = r'(            skill_path = Path\(f"skills/SKILL_\{email\[\'class\'\]\}\.md"\)\n            if not skill_path\.exists\(\):\n                skill_path = Path\(__file__\)\.parent / "skills" / f"SKILL_\{email\[\'class\'\]\}\.md"\n\n)+'
        content = re.sub(pattern, r'\1', content)

    return content

# Profiler
p = Path("mcp_university/summarizer/profiler.py")
p.write_text(fix_file(p, p.read_text(encoding="utf-8")), encoding="utf-8")

# Script
s = Path("scripts/create_person_profiles.py")
s.write_text(fix_file(s, s.read_text(encoding="utf-8")), encoding="utf-8")

# Process
proc = Path("process_sorted_emails.py")
proc_content = proc.read_text(encoding="utf-8")
# Fix the duplicate skill_path specifically
proc_content = proc_content.replace(
    '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            # Gender Determination und Salutation\n            first_name = "Unknown"\n            try:\n                with extract_msg.openMsg(str(latest_mail)) as msg:\n                    first_name = extract_firstname(msg.sender)\n            except Exception:\n                pass\n            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"',
    '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            # Gender Determination und Salutation\n            first_name = "Unknown"\n            try:\n                with extract_msg.openMsg(str(latest_mail)) as msg:\n                    first_name = extract_firstname(msg.sender)\n            except Exception:\n                pass'
)
proc.write_text(proc_content, encoding="utf-8")
