"""Tests für den EmailController."""
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies to avoid side effects during import/init
with patch('mcp_university.agent.engine.SearchIndex'),      patch('mcp_university.agent.engine.MetadataStore'),      patch('mcp_university.agent.engine.ParserFactory'):
    from mcp_university.classifier.controller import EmailController
from mcp_university.utils.outlook import create_outlook_draft

def test_parse_sorted_report(tmp_path):
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\n\n## Class\n- **S** | Name | Inbox: `D:\\mail.msg`", encoding="utf-8")
    with patch('mcp_university.classifier.controller.Agent'):
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    # Agent.chat returns a string
    mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    _, reply, _ = controller.generate_reply(mail_path)
    assert "APPOINTMENT_BOOKED" in reply

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_no_appointment_fallback(mock_agent_cls, mock_parser_cls, tmp_path):
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    # Agent.chat side effects
    mock_agent_cls.return_value.chat.side_effect = [
        "NO_APPOINTMENT_RELEVANCE",
        "NO_FINAL_SUBMISSION_RELEVANCE",
        "REPLY_NEEDED",
        "ANHANG: NEIN\nBETREFF: T\nTEXT:\nReply"
    ]

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    _, reply, _ = controller.generate_reply(mail_path)
    assert reply == "Reply"

def test_create_outlook_draft_success():
    with patch('win32com.client.Dispatch') as mock_dispatch:
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

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_no_reply_needed(mock_agent_cls, mock_parser_cls, tmp_path):
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    mock_agent_cls.return_value.chat.side_effect = [
        "NO_APPOINTMENT_RELEVANCE",
        "NO_FINAL_SUBMISSION_RELEVANCE",
        "NO_REPLY_NEEDED|Reason"
    ]
    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")
    subject, _, _ = controller.generate_reply(mail_path)
    assert subject == "NO_REPLY_NEEDED"
