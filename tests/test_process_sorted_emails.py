"""Tests für das process_sorted_emails Skript."""
import os
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

# Add project root to sys.path to make process_sorted_emails importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock win32com BEFORE importing process_sorted_emails (essential for non-Windows)
mock_win32 = MagicMock()
sys.modules["win32com"] = mock_win32
sys.modules["win32com.client"] = mock_win32.client

from process_sorted_emails import parse_sorted_report, generate_reply, create_outlook_draft, main # noqa: E402

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
@patch("process_sorted_emails.Agent")
def test_generate_reply(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort mit dem Agent."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "Original Mail Content"

    mock_agent = mock_agent_cls.return_value
    mock_agent.chat.return_value = "ANHANG: NEIN\nBETREFF: Test Betreff\nTEXT:\nThis is the generated reply"

    mock_summarizer = MagicMock()
    mock_summarizer.model = "test-model"
    # Mocking Ollama client structure to avoid attribute errors in Agent init
    mock_summarizer.client._client.base_url = "http://localhost:11434"

    mail_path = tmp_path / "test.msg"
    skill_path = tmp_path / "SKILL_Test.md"
    skill_path.write_text("Use formal language.", encoding="utf-8")

    subject, reply, should_attach = generate_reply(mock_summarizer, mail_path, "Summary Content", skill_path)

    assert subject == "Test Betreff"
    assert reply == "This is the generated reply"
    assert should_attach is False
    mock_agent.chat.assert_called_once()

@patch("process_sorted_emails.OUTLOOK_AVAILABLE", True)
@patch("process_sorted_emails.is_outlook_open", return_value=True)
def test_create_outlook_draft_success(mock_open):
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs."""
    mock_outlook = mock_win32.client.Dispatch.return_value
    mock_namespace = mock_outlook.GetNamespace.return_value

    mock_store = MagicMock()
    mock_store.DisplayName = "daniel.gaida@th-koeln.de"
    mock_root = mock_store.GetRootFolder.return_value
    mock_folder = MagicMock()
    mock_folder.Name = "Work in Progress"
    mock_root.Folders = [mock_folder]
    mock_namespace.Stores = [mock_store]

    mock_mail = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail
    mock_mail.Move.return_value = mock_mail

    success = create_outlook_draft("Test Subject", "Test Body")

    assert success is True
    mock_mail.Save.assert_called_once()
    mock_mail.Move.assert_called_with(mock_folder)
    mock_mail.Display.assert_called_with(False)
    assert mock_mail.Subject == "Test Subject"

@patch("process_sorted_emails.OUTLOOK_AVAILABLE", True)
@patch("process_sorted_emails.is_outlook_open", return_value=False)
def test_create_outlook_draft_no_outlook(mock_open):
    """Testet das Verhalten, wenn Outlook nicht geöffnet ist."""
    success = create_outlook_draft("Test Subject", "Test Body")
    assert success is False

@patch("process_sorted_emails.run_sort_emails")
@patch("process_sorted_emails.get_config")
@patch("process_sorted_emails.Summarizer")
@patch("process_sorted_emails.Agent")
@patch("process_sorted_emails.MailParser")
@patch("process_sorted_emails.create_outlook_draft")
def test_main_reporting_and_cleanup(mock_draft, mock_parser_cls, mock_agent_cls, mock_summ_cls, mock_config, mock_run_sort, tmp_path):
    """Testet die Berichterstellung und das Löschen der temporären Datei in main()."""
    source_dir = tmp_path / "emails"
    source_dir.mkdir()
    report = source_dir / "sorted_emails.md"

    # Use real paths that exist in tmp_path
    mail_path = source_dir / "mail.msg"
    mail_path.touch()

    report.write_text(f"## TestClass\n- **2024_SoSe** | TestUser | Inbox: `{mail_path}`", encoding="utf-8")

    mock_run_sort.return_value = None
    mock_draft.return_value = True

    # Mock MailParser date and parse
    mock_parser = mock_parser_cls.return_value
    mock_parser.get_email_date.return_value = datetime.now()

    # Mock Summarizer
    mock_summ = mock_summ_cls.return_value
    mock_summ.summarize_email_conversation.return_value = "Test Summary"
    mock_summ.client._client.base_url = "http://localhost:11434"

    # Mock Agent
    mock_agent = mock_agent_cls.return_value
    mock_agent.chat.return_value = "ANHANG: NEIN\nBETREFF: Test\nTEXT:\nReply"

    # Call main with args
    with patch("sys.argv", ["process_sorted_emails.py", str(source_dir), "--config", "config.yaml"]):
        # Mock parts to contain "Inbox" but not "SentItems"
        with patch.object(Path, "parts", property(lambda x: ("Inbox",))):
            main()

    # Verify processed_emails.md exists
    processed_report = source_dir / "processed_emails.md"
    assert processed_report.exists()
    assert "TestUser" in processed_report.read_text(encoding="utf-8")

    # Verify sorted_emails.md is deleted
    assert not report.exists()
