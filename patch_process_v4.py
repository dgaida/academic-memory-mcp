import re
from pathlib import Path

path = Path("process_sorted_emails.py")
content = path.read_text(encoding="utf-8")

# 1. Clear duplicates and previous mess
content = content.replace('        student_email = ""\n        student_email = ""', '        student_email = ""')

# 2. Insert person_profile after student_email is definite
content = content.replace('        except Exception:\n            pass', '        except Exception:\n            pass\n\n        person_profile = profiler.get_profile(student_email) if student_email else None')

# 3. Ensure skill_path is defined in both branches
# Branch 1: is_ba_ma
if 'skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")' not in content:
    content = content.replace('            # Gender Determination', '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            # Gender Determination')

# Branch 2: else (non-BA/MA)
# Find where it starts
content = content.replace('            gender_salutation = summarizer.determine_gender(first_name)', '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            gender_salutation = summarizer.determine_gender(first_name)')

path.write_text(content, encoding="utf-8")
