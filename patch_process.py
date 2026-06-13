import re
from pathlib import Path

path = Path("process_sorted_emails.py")
content = path.read_text(encoding="utf-8")

# 1. Ensure Import
if "from mcp_university.summarizer.profiler import PersonProfiler" not in content:
    content = content.replace("from mcp_university.agent import Agent", "from mcp_university.agent import Agent\nfrom mcp_university.summarizer.profiler import PersonProfiler")

# 2. Ensure profiler initialization in main
# We need to find the correct main function and where we initialized mail_parser
if "profiler = PersonProfiler()" not in content:
    content = content.replace("mail_parser = MailParser()", "mail_parser = MailParser()\n    profiler = PersonProfiler()")

# 3. Fix the processing loop
# We need to find the for email in emails loop
# And ensure student_email, skill_path etc are defined in each branch.

# Let's try to find the loop start
loop_start = "    for email in emails:"
if loop_start in content:
    # We want to insert person_profile = None at the top of the loop
    # and find where student_email is defined.
    pass

# Actually, my previous edits were quite messy.
# Let's use a more robust replacement strategy for the two main processing blocks.

# BLOCK 1: is_ba_ma
block1_old_pattern = r'if is_ba_ma:.*?reply_subject, reply, should_attach = generate_reply\(.*?agent,.*?latest_mail,.*?additional_context=additional_context,.*?debug=args\.debug,.*?appointment_skill_path=appointment_skill_path,.*?sender_name=sender_name,.*?sender_email=student_email,.*?\)'
# This is too hard to regex.

# Let's just do a targeted search and replace for the problematic areas.

# Fix F821 in process_sorted_emails.py:795 (student_email)
# It was: person_profile = profiler.get_profile(student_email) if student_email else None
# but student_email wasn't defined yet.

content = re.sub(r'person_profile = profiler\.get_profile\(student_email\) if student_email else None', '', content)

# Find where student_email is defined (around line 890+)
content = content.replace('        sender_name = ""', '        sender_name = ""\n        student_email = ""') # just in case
content = content.replace('                student_email = msg.sender', '                student_email = msg.sender')

# Insert person_profile after student_email is extracted
content = content.replace('            pass\n\n        if is_ba_ma:', '            pass\n\n        person_profile = profiler.get_profile(student_email) if student_email else None\n        if is_ba_ma:')

# Fix Undefined name `skill_path`
# skill_path needs to be defined BEFORE generate_reply

# In the is_ba_ma block:
if 'skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")' not in content:
     # We need to re-add it if it was removed
     content = content.replace('            # Gender Determination', '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            # Gender Determination')

# Ensure generate_reply call uses skill_path
# (Already does, but ruff says it's undefined because I probably removed the definition)

# Let's do the same for the second block (non-BA/MA)
# Around line 1132
if 'skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")' not in content:
    # Find a good anchor
    content = content.replace('            gender_salutation = summarizer.determine_gender(first_name)', '            skill_path = Path(f"skills/SKILL_{email[\'class\']}.md")\n            if not skill_path.exists():\n                skill_path = Path(__file__).parent / "skills" / f"SKILL_{email[\'class\']}.md"\n\n            gender_salutation = summarizer.determine_gender(first_name)')

path.write_text(content, encoding="utf-8")
