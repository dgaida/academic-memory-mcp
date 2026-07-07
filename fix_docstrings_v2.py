import sys
from pathlib import Path

path = Path('scripts/process_sorted_emails.py')
content = path.read_text(encoding='utf-8')

# The signature changed in my previous edits!
old_handle = '                    def handle_remove_to_tab2(t1_mails, t2_mails, *all_states):'
# Searching for the actual line from my UI change
actual_handle = '                    def handle_remove_to_tab2(t1_mails, t2_mails, *all_states):'

# Wait, I used *all_states in the script. Let's find it.
lines = content.splitlines()
for i, line in enumerate(lines):
    if 'def handle_remove_to_tab2' in line:
        print(f"Found at line {i+1}: {line}")
        if '"""' not in lines[i+1]:
            lines.insert(i+1, '                        """Verarbeitet das Verschieben von Mails von Tab 1 nach Tab 2."""')

path.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
