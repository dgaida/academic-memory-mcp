"""Tests für das process_sorted_emails Skript."""
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Add project root to sys.path to make process_sorted_emails importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock win32com BEFORE importing process_sorted_emails (essential for non-Windows)
mock_win32 = MagicMock()
sys.modules["win32com"] = mock_win32
sys.modules["win32com.client"] = mock_win32.client

# Import after mocks and sys.path update
from process_sorted_emails import parse_sorted_report, generate_reply, create_outlook_draft  # noqa: E402

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
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin gebucht wurde (Schritt 1)."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "Ich nehme den Termin am Montag."

    mock_agent = mock_agent_cls.return_value
    # Schritt 1 gibt APPOINTMENT_BOOKED zurück
    mock_agent.chat.return_value = "APPOINTMENT_BOOKED"

    mock_summarizer = MagicMock()
    mock_summarizer.model = "test-model"
    mock_summarizer.client._client.base_url = "http://localhost:11434"

    mail_path = tmp_path / "test.msg"

    subject, reply, should_attach = generate_reply(mock_agent, mail_path)

    assert reply == "APPOINTMENT_BOOKED"
    assert mock_agent.chat.call_count == 1

@patch("process_sorted_emails.MailParser")
@patch("process_sorted_emails.Agent")
def test_generate_reply_no_appointment_fallback(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet den Fallback auf die reguläre Antwort (Schritt 2)."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "Frage zu Thesis."

    mock_agent = mock_agent_cls.return_value
    # Schritt 1: Nicht terminrelevant
    # Schritt 1.2: Keine finale Abgabe
    # Schritt 1.5: Antwort erforderlich
    # Schritt 2: Reguläre Antwort
    mock_agent.chat.side_effect = [
        "NO_APPOINTMENT_RELEVANCE",
        "NO_FINAL_SUBMISSION_RELEVANCE",
        "REPLY_NEEDED",
        "ANHANG: NEIN\nBETREFF: Thesis\nTEXT:\nHier ist die Antwort."
    ]

    mock_summarizer = MagicMock()
    mock_summarizer.model = "test-model"
    mock_summarizer.client._client.base_url = "http://localhost:11434"

    mail_path = tmp_path / "test.msg"

    subject, reply, should_attach = generate_reply(mock_agent, mail_path)

    assert subject == "Thesis"
    assert reply == "Hier ist die Antwort."
    assert mock_agent.chat.call_count == 4

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

    # Mocking Folders which might be a collection
    mock_root.Folders = [mock_folder]
    mock_namespace.Stores = [mock_store]

    mock_mail = MagicMock()
    # Mock fallback if folder not found
    mock_outlook.CreateItem.return_value = mock_mail
    # Mock folder Add if found
    mock_folder.Items.Add.return_value = mock_mail

    success = create_outlook_draft("Test Subject", "Test Body")

    assert success is True
    mock_mail.Save.assert_called_once()
    mock_mail.Display.assert_called_with(False)
    assert mock_mail.Subject == "Test Subject"

@patch("process_sorted_emails.OUTLOOK_AVAILABLE", True)
@patch("process_sorted_emails.is_outlook_open", return_value=False)
def test_create_outlook_draft_no_outlook(mock_open):
    """Testet das Verhalten, wenn Outlook nicht geöffnet ist."""
    success = create_outlook_draft("Test Subject", "Test Body")
    assert success is False

@patch("process_sorted_emails.MailParser")
@patch("process_sorted_emails.Agent")
def test_generate_reply_no_reply_needed(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Erkennung, dass keine Antwort erforderlich ist."""
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "Vielen Dank für die Information!"
    mock_parser.extract_latest_message.return_value = "Vielen Dank für die Information!"

    mock_agent = mock_agent_cls.return_value
    # Schritt 1: Nicht terminrelevant
    # Schritt 1.2: Keine finale Abgabe
    # Schritt 1.5: Keine Antwort erforderlich
    mock_agent.chat.side_effect = [
        "NO_APPOINTMENT_RELEVANCE",
        "NO_FINAL_SUBMISSION_RELEVANCE",
        "NO_REPLY_NEEDED|Reine Dankesmail ohne Fragen."
    ]

    mail_path = tmp_path / "test.msg"

    subject, reply, should_attach = generate_reply(mock_agent, mail_path)

    assert subject == "NO_REPLY_NEEDED"
    assert "Reine Dankesmail" in reply
    assert mock_agent.chat.call_count == 3

def test_age_months_logic():
    """Verifiziert die Logik für das Alter in Monaten."""
    age_months = 3
    cutoff = datetime.now() - timedelta(days=age_months * 30)
    cutoff = cutoff.replace(tzinfo=None)

    # E-Mail von heute (sollte nicht übersprungen werden)
    mail_date_new = datetime.now().replace(tzinfo=None)
    assert mail_date_new >= cutoff

    # E-Mail von vor 4 Monaten (sollte übersprungen werden)
    mail_date_old = datetime.now() - timedelta(days=120)
    mail_date_old = mail_date_old.replace(tzinfo=None)
    assert mail_date_old < cutoff
