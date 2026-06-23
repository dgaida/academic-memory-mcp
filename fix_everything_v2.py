from pathlib import Path
import re

# 1. Fix mcp_university/classifier/controller.py
p = Path('mcp_university/classifier/controller.py')
c = p.read_text(encoding='utf-8')

# Ensure all processed_results are self.processed_results
# (avoiding double self.self. if already fixed)
c = re.sub(r'(?<!self\.)processed_results', 'self.processed_results', c)

# Fix E701: Multiple statements on one line
c = c.replace('if not results: return', 'if not results:\n            return')

p.write_text(c, encoding='utf-8')

# 2. Fix tests/test_process_sorted_emails.py
p2 = Path('tests/test_process_sorted_emails.py')
c2 = p2.read_text(encoding='utf-8')
lines = c2.splitlines()

# Extract all imports
std_imports = []
other_lines = []
for line in lines:
    if line.startswith('import ') or (line.startswith('from ') and 'mcp_university' not in line):
        std_imports.append(line)
    else:
        other_lines.append(line)

# Put std imports at the top
new_test_content = "\n".join(sorted(list(set(std_imports)))) + "\n\n" + "\n".join(other_lines)
p2.write_text(new_test_content, encoding='utf-8')

# 3. Ensure other tests are consistent
for test_file in ['tests/test_age_logic.py', 'tests/test_delayed_summary.py']:
    tp = Path(test_file)
    if tp.exists():
        tc = tp.read_text(encoding='utf-8')
        # They might use local processed_results, which might cause NameError if not handled.
        # But wait, the NameError was in controller.py during execution.
        # So fixing controller.py should solve it.
