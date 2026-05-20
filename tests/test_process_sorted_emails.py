"""Tests für das process_sorted_emails Skript."""
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path to make process_sorted_emails importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock win32com BEFORE importing process_sorted_emails
mock_win32 = MagicMock()
sys.modules["win32com"] = mock_win32
sys.modules["win32com.client"] = mock_win32.client

from process_sorted_emails import parse_sorted_report, generate_reply, create_outlook_draft # noqa: E402

def test_parse_sorted_report(tmp_path):
    """Testet das Parsen des sorted_emails.md Reports."""
    report = tmp_path / "sorted_emails.md"
    report.write_text("""# Sortierte E-Mails

## BachelorThesis
- **2024_SoSe** | Mustermann | Inbox: `D:\\TH_Koeln\\StudentMails\\BachelorThesis\\2024_SoSe\\Mustermann\\Inbox\\mail1.msg`
- **2024_SoSe** | Schmidt | SentItems: `D:\\TH_Koeln\\StudentMails\\BachelorThesis\\2024_SoSe\\Schmidt\\SentItems\\mail2.msg`

## MasterThesis
- **2023_24_WS** | Doe | Inbox: `D:\\TH_Koeln\\StudentMails\\MasterThesis\\2023_24_WS\\Doe\\Inbox\\mail3.msg`
""", encoding="utf-8")

    emails = parse_sorted_report(report)
    assert len(emails) == 3
    assert emails[0]["class"] == "BachelorThesis"
    assert emails[0]["lastname"] == "Mustermann"
    assert emails[0]["folder"] == "Inbox"
    assert emails[2]["class"] == "MasterThesis"

@patch("process_sorted_emails.MailParser")
def test_generate_reply(mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort mit dem LLM."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "Original Mail Content"

    mock_summarizer = MagicMock()
    mock_summarizer.model = "test-model"
    mock_summarizer.client.chat.return_value = {
        "message": {"content": "This is the generated reply"}
    }

    mail_path = tmp_path / "test.msg"
    skill_path = tmp_path / "SKILL_Test.md"
    skill_path.write_text("Use formal language.", encoding="utf-8")

    reply = generate_reply(mock_summarizer, mail_path, "Summary Content", skill_path)

    assert reply == "This is the generated reply"
    mock_summarizer.client.chat.assert_called_once()

@patch("process_sorted_emails.OUTLOOK_AVAILABLE", True)
def test_create_outlook_draft_success():
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs."""
    mock_outlook = MagicMock()
    mock_mail = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail

    with patch("win32com.client.GetActiveObject", return_value=mock_outlook):
        success = create_outlook_draft("Test Subject", "Test Body")

    assert success is True
    mock_mail.Save.assert_called_once()
    assert mock_mail.Subject == "Re: Test Subject"

@patch("process_sorted_emails.OUTLOOK_AVAILABLE", True)
def test_create_outlook_draft_no_outlook():
    """Testet das Verhalten, wenn Outlook nicht geöffnet ist."""
    with patch("win32com.client.GetActiveObject", side_effect=Exception("Not running")):
        success = create_outlook_draft("Test Subject", "Test Body")

    assert success is False
