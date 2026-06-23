from pathlib import Path
import re

p = Path('mcp_university/classifier/controller.py')
c = p.read_text(encoding='utf-8')

# Ensure self.processed_results is initialized in __init__
if 'self.processed_results = []' not in c:
    c = c.replace('self.use_action_classifier = use_action_classifier', 'self.use_action_classifier = use_action_classifier\n        self.processed_results = []')

# Fix any remaining bare processed_results.append or access
# Use regex to find processed_results that is NOT preceded by self. or a dot (like res['status'])
# and NOT part of a string
c = re.sub(r'(?<![.\w])processed_results(?!\s*\[)', 'self.processed_results', c)

# Fix the report writing method formatting
method_pattern = re.compile(r'def write_processed_report\(self, source_dir, results\):.*?logger\.info\(f"Bericht in \{report_path\} geschrieben\."\)', re.DOTALL)
new_method = """    def write_processed_report(self, source_dir, results):
        \"\"\"Schreibt den Abschlussbericht über verarbeitete E-Mails.

        Args:
            source_dir (Path): Quellverzeichnis.
            results (list): Liste von Dictionaries mit 'lastname', 'subject', 'status'.

        Returns:
            None
        \"\"\"
        if not results:
            return
        report_path = source_dir / "processed_emails.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Verarbeitete E-Mails\\n\\n")
            f.write("| Student | Betreff | Status |\\n")
            f.write("| :--- | :--- | :--- |\\n")
            for res in results:
                f.write(f"| {res.get('lastname', 'Unknown')} | {res.get('subject', 'No Subject')} | {res.get('status', 'Unknown')} |\\n")
        logger.info(f"Bericht in {report_path} geschrieben.")"""

if method_pattern.search(c):
    c = method_pattern.sub(new_method, c)

p.write_text(c, encoding='utf-8')
