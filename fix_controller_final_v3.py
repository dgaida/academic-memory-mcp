import sys
from pathlib import Path
import re

p = Path('mcp_university/classifier/controller.py')
content = p.read_text(encoding='utf-8')

# Ensure self.processed_results is initialized in __init__
if 'self.processed_results = []' not in content:
    content = content.replace('self.use_action_classifier = use_action_classifier', 'self.use_action_classifier = use_action_classifier\n        self.processed_results = []')

# Fix bare processed_results to self.processed_results
content = re.sub(r'(?<!self\.)processed_results(?!\s*\[)', 'self.processed_results', content)

# Define the exact method text
# We use raw string and double backslashes to ensure \n is written as \n
new_method = r"""    def write_processed_report(self, source_dir, results):
        """Schreibt den Abschlussbericht über verarbeitete E-Mails.

        Args:
            source_dir (Path): Quellverzeichnis.
            results (list): Liste von Dictionaries mit 'lastname', 'subject', 'status'.

        Returns:
            None
        """
        if not results:
            return

        report_path = source_dir / "processed_emails.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Verarbeitete E-Mails\n\n")
            f.write("| Student | Betreff | Status |\n")
            f.write("| :--- | :--- | :--- |\n")
            for res in results:
                f.write(
                    f"| {res.get('lastname', 'Unknown')} | "
                    f"{res.get('subject', 'No Subject')} | "
                    f"{res.get('status', 'Unknown')} |\n"
                )
        logger.info(f"Bericht in {report_path} geschrieben.")
"""

# Replace from the 'if self.processed_results:' block to 'def generate_short_summary'
area_pattern = re.compile(r'if self\.processed_results:.*?def generate_short_summary', re.DOTALL)

# Reconstruct the replacement to include the if block and the return
full_replacement = """if self.processed_results:
            self.write_processed_report(source_dir, self.processed_results)

        return emails_to_process

""" + new_method + "\n    def generate_short_summary"

if area_pattern.search(content):
    content = area_pattern.sub(full_replacement, content)
    p.write_text(content, encoding='utf-8')
    print("Success")
else:
    print("Pattern not found")
