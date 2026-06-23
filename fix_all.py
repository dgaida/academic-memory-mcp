from pathlib import Path
import re

# 1. Fix controller.py
p = Path('mcp_university/classifier/controller.py')
c = p.read_text(encoding='utf-8')

# Fix undefined processed_results
c = c.replace('if processed_results:', 'if self.processed_results:')
c = c.replace('for res in processed_results:', 'for res in self.processed_results:')

# Fix E701: Multiple statements on one line
c = c.replace('if not results: return', 'if not results:\n            return')

p.write_text(c, encoding='utf-8')

# 2. Fix tests/test_process_sorted_emails.py
p2 = Path('tests/test_process_sorted_emails.py')
content = p2.read_text(encoding='utf-8')

# Move imports to top and fix the structure
# Let's just rewrite it to be clean and not mess with sys.modules globally if possible,
# or at least do it more carefully.

new_test_content = """import os
import sys
from unittest.mock import MagicMock, patch
from mcp_university.utils.outlook import create_outlook_draft

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We must be careful with sys.modules as it affects other tests in the same process.
# However, for this specific test file, we need them mocked to even import EmailController
# if the environment is missing them.

def setup_mocks():
    mock_modules = [
        'torch', 'sentence_transformers', 'xgboost', 'qdrant_client',
        'rank_bm25', 'extract_msg', 'sklearn', 'sklearn.metrics',
        'sklearn.metrics.pairwise', 'sklearn.ensemble',
        'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
        'sklearn.preprocessing', 'pydantic', 'yaml', 'dotenv'
    ]
    for module in mock_modules:
        sys.modules[module] = MagicMock()

    # Special case for torch.Tensor
    sys.modules['torch'].Tensor = type('Tensor', (), {})

setup_mocks()

# Now import EmailController
with patch('mcp_university.classifier.controller.get_config'), \\
     patch('mcp_university.classifier.controller.MailParser'), \\
     patch('mcp_university.classifier.controller.PersonProfiler'), \\
     patch('mcp_university.classifier.controller.Summarizer'):
    from mcp_university.classifier.controller import EmailController

def test_parse_sorted_report(tmp_path):
    \"\"\"Prüft das Parsen des sortierten E-Mail Reports.

    Args:
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    \"\"\"
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\\n\\n## Class\\n- **S** | Name | Inbox: `D:\\\\mail.msg`", encoding="utf-8")
    with patch('mcp_university.classifier.controller.Agent'), \\
         patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1

def test_processed_emails_report_generation(tmp_path):
    \"\"\"Prüft die Generierung des processed_emails.md Berichts.

    Dieser Test verifiziert, dass die Methode write_processed_report eine Datei
    erstellt, die alle übergebenen Ergebnisse im korrekten Markdown-Format enthält.

    Args:
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    \"\"\"
    with patch('mcp_university.classifier.controller.Agent'), \\
         patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
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
    \"\"\"Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    \"\"\"
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    with patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController(debug=False)
        mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"
        mock_agent_cls.return_value.last_appointment_info = {"start_time": "2026-06-22 14:00"}
        mock_agent_cls.return_value.last_tool_error = None

        mail_path = tmp_path / "test.msg"
        mail_path.write_text("dummy")

        _, reply, _ = controller.generate_reply(mail_path)
        assert "APPOINTMENT_BOOKED" in reply
"""

p2.write_text(new_test_content, encoding='utf-8')
