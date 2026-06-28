"""Tests für den EmailController."""
import os
import sys
from unittest.mock import MagicMock, patch

# Mock heavy dependencies
mock_modules = [
    'torch',
    'torch.nn',
    'transformers',
    'sentence_transformers',
    'xgboost',
    'gradio',
    'qdrant_client',
    'docling',
    'liteparse',
    'sklearn.metrics.pairwise'
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

class MockTensor:
    pass
sys.modules['torch'].Tensor = MockTensor

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ruff: noqa: E402
from mcp_university.classifier.controller import EmailController
from mcp_university.utils.outlook import create_outlook_draft

def test_parse_sorted_report(tmp_path):
    """Prüft das Parsen des sortierten E-Mail Reports."""
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte E-Mails\n\n## Class\n| Semester | Nachname | Ordner | Datei |\n| --- | --- | --- | --- |\n| 2025_SoSe | Name | Inbox | D:\\\\mail.msg |", encoding="utf-8")
    with patch('mcp_university.classifier.controller.Agent'):
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1
        assert emails[0]["lastname"] == "Name"
        assert str(emails[0]["path"]) == "D:\\\\mail.msg"

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    # Agent.chat returns a string
    mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"
    mock_agent_cls.return_value.last_appointment_info = {"start_time": "2026-06-22 14:00"}
    mock_agent_cls.return_value.last_tool_error = None

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    _, reply, _ = controller.generate_reply(mail_path)
    assert "APPOINTMENT_BOOKED" in reply

def test_create_outlook_draft_success():
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs."""
    with patch('win32com.client.Dispatch', create=True) as mock_dispatch:
        mock_outlook = mock_dispatch.return_value
        mock_namespace = mock_outlook.GetNamespace.return_value
        mock_store = MagicMock()
        mock_store.DisplayName = "test@example.com"
        mock_namespace.Stores = [mock_store]
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders = []

        mock_mail = MagicMock()
        mock_outlook.CreateItem.return_value = mock_mail

        with patch('mcp_university.utils.outlook.get_config') as mock_cfg:
            mock_cfg.return_value.user.email = "test@example.com"
            success = create_outlook_draft("S", "B")
            assert success is True
