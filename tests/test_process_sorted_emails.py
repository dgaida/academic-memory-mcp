"""Tests for the EmailController and report generation."""
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock all heavy third-party libraries at module level BEFORE project imports
mock_modules = [
    'torch', 'sentence_transformers', 'xgboost', 'qdrant_client',
    'rank_bm25', 'extract_msg', 'sklearn', 'sklearn.metrics',
    'sklearn.metrics.pairwise', 'sklearn.ensemble',
    'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
    'sklearn.preprocessing', 'pydantic', 'yaml', 'dotenv', 'transformers', 'ollama'
]
for module in mock_modules:
    sys.modules[module] = MagicMock()

if 'torch' in sys.modules:
    sys.modules['torch'].Tensor = type('Tensor', (), {})

# Mock internal submodules
sys.modules['mcp_university.agent'] = MagicMock()
sys.modules['mcp_university.agent.mcp_agent'] = MagicMock()
sys.modules['mcp_university.agent.engine'] = MagicMock()
sys.modules['mcp_university.classifier.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.profiler'] = MagicMock()
sys.modules['mcp_university.utils.llm_client_wrapper'] = MagicMock()

# Import project modules
from mcp_university.utils.outlook import create_outlook_draft

# Now define the test class/functions
# We will mock EmailController's dependencies in a setup fixture or similar
# but for now let's just use patches in each test.

@patch('mcp_university.classifier.controller.get_config')
@patch('mcp_university.classifier.controller.MailParser')
@patch('mcp_university.classifier.controller.PersonProfiler')
@patch('mcp_university.classifier.controller.Summarizer')
@patch('mcp_university.classifier.controller.Agent')
def test_parse_sorted_report(mock_agent, mock_summarizer, mock_profiler, mock_parser, mock_config, tmp_path):
    """Prüft das Parsen des sortierten E-Mail Reports."""
    from mcp_university.classifier.controller import EmailController
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\n\n## Class\n- **S** | Name | Inbox: `D:\\mail.msg`", encoding="utf-8")

    controller = EmailController()
    emails = controller.parse_report(report)
    assert len(emails) == 1

@patch('mcp_university.classifier.controller.get_config')
@patch('mcp_university.classifier.controller.MailParser')
@patch('mcp_university.classifier.controller.PersonProfiler')
@patch('mcp_university.classifier.controller.Summarizer')
@patch('mcp_university.classifier.controller.Agent')
def test_processed_emails_report_generation(mock_agent, mock_summarizer, mock_profiler, mock_parser, mock_config, tmp_path):
    """Prüft die Generierung des processed_emails.md Berichts."""
    from mcp_university.classifier.controller import EmailController
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

@patch('mcp_university.classifier.controller.get_config')
@patch('mcp_university.classifier.controller.MailParser')
@patch('mcp_university.classifier.controller.PersonProfiler')
@patch('mcp_university.classifier.controller.Summarizer')
@patch('mcp_university.classifier.controller.Agent')
def test_generate_reply_appointment_booked(mock_agent_cls, mock_summarizer, mock_profiler, mock_parser_cls, mock_config, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde."""
    from mcp_university.classifier.controller import EmailController
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"

    controller = EmailController(debug=False)
    controller.agent.chat.return_value = "APPOINTMENT_BOOKED"
    controller.agent.last_appointment_info = {"start_time": "2026-06-22 14:00"}
    controller.agent.last_tool_error = None

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    _, reply, _ = controller.generate_reply(mail_path)
    assert "APPOINTMENT_BOOKED" in reply

def test_create_outlook_draft_success():
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs."""
    with patch('win32com.client.Dispatch') as mock_dispatch:
        mock_outlook = mock_dispatch.return_value
        mock_outlook.GetNamespace.return_value.Stores = [MagicMock(DisplayName="test@example.com")]
        mock_outlook.CreateItem.return_value = MagicMock()

        with patch('mcp_university.utils.outlook.get_config') as mock_cfg:
            mock_cfg.return_value.user.email = "test@example.com"
            success = create_outlook_draft("S", "B")
            assert success is True
