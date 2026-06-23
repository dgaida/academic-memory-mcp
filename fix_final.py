import sys
from pathlib import Path
import re

# 1. Fix controller.py
p = Path('mcp_university/classifier/controller.py')
content = p.read_text(encoding='utf-8')

# Ensure self.processed_results is initialized in __init__
if 'self.processed_results = []' not in content:
    content = content.replace(
        'self.use_action_classifier = use_action_classifier',
        'self.use_action_classifier = use_action_classifier\n        self.processed_results = []'
    )

# Standardize processed_results references
content = re.sub(r'(?<!self\.)(?<!\w)processed_results(?!\s*\[)', 'self.processed_results', content)

# Brute force replace the block that was repeatedly corrupted
# We match from the end of the loop in process_all_emails to the start of generate_short_summary
corrupted_pattern = re.compile(r'# Always return emails_to_process for GUI consistency.*?def generate_short_summary', re.DOTALL)

clean_block = """# Always return emails_to_process for GUI consistency

        if self.processed_results:
            self.write_processed_report(source_dir, self.processed_results)

        return emails_to_process

    def write_processed_report(self, source_dir: Path, results: list):
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
                name = res.get('lastname', 'Unknown')
                subj = res.get('subject', 'No Subject')
                stat = res.get('status', 'Unknown')
                f.write(f"| {name} | {subj} | {stat} |\\n")
        logger.info(f"Bericht in {report_path} geschrieben.")

    def generate_short_summary"""

if corrupted_pattern.search(content):
    content = corrupted_pattern.sub(clean_block, content)
else:
    print("Corrupted block pattern not found")

# Fix the f-string issue for Ruff
content = content.replace('prompt = f"Fasse die folgende', 'prompt = "Fasse die folgende')

p.write_text(content, encoding='utf-8')
print("Success controller")

# 2. Fix test file
p2 = Path('tests/test_process_sorted_emails.py')
test_content = """\"\"\"Tests for the EmailController and report generation.\"\"\"
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock all heavy third-party libraries at module level
mock_modules = [
    'torch', 'sentence_transformers', 'xgboost', 'qdrant_client',
    'rank_bm25', 'extract_msg', 'sklearn', 'sklearn.metrics',
    'sklearn.metrics.pairwise', 'sklearn.ensemble',
    'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
    'sklearn.preprocessing', 'pydantic', 'yaml', 'dotenv', 'transformers', 'ollama'
]
for module in mock_modules:
    if module not in sys.modules:
        sys.modules[module] = MagicMock()

if 'torch' in sys.modules:
    sys.modules['torch'].Tensor = type('Tensor', (), {})

# Mock internal submodules
sys.modules['mcp_university.agent'] = MagicMock()
sys.modules['mcp_university.agent.mcp_agent'] = MagicMock()
sys.modules['mcp_university.agent.engine'] = MagicMock()
sys.modules['mcp_university.classifier.engine'] = MagicMock()

from mcp_university.utils.outlook import create_outlook_draft

# Import EmailController after mocks are set up
with patch('mcp_university.classifier.controller.get_config'), \\
     patch('mcp_university.classifier.controller.MailParser'), \\
     patch('mcp_university.classifier.controller.PersonProfiler'), \\
     patch('mcp_university.classifier.controller.Summarizer'):
    from mcp_university.classifier.controller import EmailController

def test_parse_sorted_report(tmp_path):
    \"\"\"Prüft das Parsen des sortierten E-Mail Reports.\"\"\"
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\\n\\n## Class\\n- **S** | Name | Inbox: `D:\\\\mail.msg`", encoding="utf-8")

    mock_config = MagicMock()
    with patch('mcp_university.classifier.controller.Agent'), \\
         patch('mcp_university.classifier.controller.get_config', return_value=mock_config):
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1

def test_processed_emails_report_generation(tmp_path):
    \"\"\"Prüft die Generierung des processed_emails.md Berichts.\"\"\"
    mock_config = MagicMock()
    with patch('mcp_university.classifier.controller.Agent'), \\
         patch('mcp_university.classifier.controller.get_config', return_value=mock_config):
        controller = EmailController()
        results = [
            {"lastname": "Mustermann", "subject": "Frage", "status": "Beantwortet"},
            {"lastname": "Schmidt", "subject": "Termin", "status": "Archiviert"}
        ]

        controller.write_processed_report(tmp_path, results)

        report_file = tmp_path / "processed_emails.md"
        assert report_file.exists()

        content = report_file.read_text(encoding="utf-8")
        assert "# Verarbeitete E-Mails" in content
        assert "| Mustermann | Frage | Beantwortet |" in content
        assert "| Schmidt | Termin | Archiviert |" in content

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    \"\"\"Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde.\"\"\"
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    mock_config = MagicMock()
    with patch('mcp_university.classifier.controller.get_config', return_value=mock_config):
        controller = EmailController(debug=False)
        mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"
        mock_agent_cls.return_value.last_appointment_info = {"start_time": "2026-06-22 14:00"}
        mock_agent_cls.return_value.last_tool_error = None

        mail_path = tmp_path / "test.msg"
        mail_path.write_text("dummy")

        _, reply, _ = controller.generate_reply(mail_path)
        assert "APPOINTMENT_BOOKED" in reply
"""
p2.write_text(test_content, encoding='utf-8')
print("Success test")
