import sys
from pathlib import Path

p = Path('mcp_university/classifier/controller.py')
lines = p.read_text(encoding='utf-8').splitlines()

# 1. Ensure self.processed_results is initialized in __init__
init_line = -1
for i, line in enumerate(lines):
    if 'def __init__' in line:
        init_line = i
    if init_line != -1 and 'self.use_action_classifier = use_action_classifier' in line:
        if 'self.processed_results = []' not in lines[i+1]:
            lines.insert(i+1, '        self.processed_results = []')
        break

# 2. Fix the area around process_all_emails end and write_processed_report
new_lines = []
skip = False
for line in lines:
    if 'if self.processed_results:' in line and 'self.write_processed_report' in lines[lines.index(line)+1]:
        # This is the start of the block I want to keep clean
        new_lines.append('        if self.processed_results:')
        new_lines.append('            self.write_processed_report(source_dir, self.processed_results)')
        new_lines.append('')
        new_lines.append('        return emails_to_process')
        new_lines.append('')
        new_lines.append('    def write_processed_report(self, source_dir: Path, results: list):')
        new_lines.append('        """Schreibt den Abschlussbericht über verarbeitete E-Mails.')
        new_lines.append('')
        new_lines.append('        Args:')
        new_lines.append('            source_dir (Path): Quellverzeichnis.')
        new_lines.append('            results (list): Liste von Dictionaries mit \'lastname\', \'subject\', \'status\'.')
        new_lines.append('')
        new_lines.append('        Returns:')
        new_lines.append('            None')
        new_lines.append('        """')
        new_lines.append('        if not results:')
        new_lines.append('            return')
        new_lines.append('')
        new_lines.append('        report_path = source_dir / "processed_emails.md"')
        new_lines.append('        with open(report_path, "w", encoding="utf-8") as f:')
        new_lines.append('            f.write("# Verarbeitete E-Mails\\n\\n")')
        new_lines.append('            f.write("| Student | Betreff | Status |\\n")')
        new_lines.append('            f.write("| :--- | :--- | :--- |\\n")')
        new_lines.append('            for res in results:')
        new_lines.append('                name = res.get(\'lastname\', \'Unknown\')')
        new_lines.append('                subj = res.get(\'subject\', \'No Subject\')')
        new_lines.append('                stat = res.get(\'status\', \'Unknown\')')
        new_lines.append('                f.write(f"| {name} | {subj} | {stat} |\\n")')
        new_lines.append('        logger.info(f"Bericht in {report_path} geschrieben.")')
        skip = True
        continue

    if skip:
        if 'def generate_short_summary' in line:
            new_lines.append('')
            new_lines.append(line)
            skip = False
        continue

    new_lines.append(line)

# Also need to make sure all processed_results are self.processed_results
for i, line in enumerate(new_lines):
    if 'processed_results.append' in line and 'self.processed_results.append' not in line:
        new_lines[i] = line.replace('processed_results.append', 'self.processed_results.append')

p.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
