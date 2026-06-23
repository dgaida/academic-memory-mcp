"""Tests für den EmailController und die Berichterstellung."""
import os
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

# Projekt-Root zum sys.path hinzufügen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mcp_university.agent.engine  # noqa: F401

# Mocking von Abhängigkeiten, um Seiteneffekte beim Import/Init zu vermeiden
with patch('mcp_university.agent.engine.SearchIndex'), \
     patch('mcp_university.agent.engine.MetadataStore'), \
     patch('mcp_university.agent.engine.ParserFactory'):
    from mcp_university.classifier.controller import EmailController
from mcp_university.utils.outlook import create_outlook_draft

def test_parse_sorted_report(tmp_path):
    """Prüft das Parsen des sortierten E-Mail Reports.

    Args:
        tmp_path (pathlib.Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\n\n## Class\n- **S** | Name | Inbox: `D:\\mail.msg`", encoding="utf-8")
    with patch('mcp_university.classifier.controller.Agent'):
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (pathlib.Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
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

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_no_appointment_fallback(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet den Fallback der Antwortgenerierung, wenn keine Terminterrelevanz vorliegt.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (pathlib.Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
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
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs.

    Args:
        None

    Returns:
        None
    """
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
    """Testet die Generierung einer Antwort, wenn keine Antwort erforderlich ist.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (pathlib.Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
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

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
@patch("mcp_university.classifier.controller.Summarizer")
def test_processed_emails_generation_old_email(mock_summarizer_cls, mock_agent_cls, mock_parser_cls, tmp_path):
    """
    Testet, ob 'processed_emails.md' für alte E-Mails erstellt wird.

    Dieser Test prüft, ob eine E-Mail, die älter als der angegebene Schwellenwert ist,
    automatisch übersprungen wird und dieser Status in der Datei 'processed_emails.md'
    festgehalten wird, auch wenn der Aktions-Klassifizierer aktiviert ist.

    Args:
        mock_summarizer_cls (MagicMock): Mock für die Summarizer-Klasse.
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (pathlib.Path): Temporäres Verzeichnis von Pytest (Fixture).

    Returns:
        None
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    student_dir = source_dir / "OldStudent"
    inbox_dir = student_dir / "Inbox"
    inbox_dir.mkdir(parents=True)
    mail_file = inbox_dir / "old_test.msg"
    mail_file.write_text("dummy content")

    report_path = source_dir / "sorted_emails.md"
    report_path.write_text("# Sortierte\n\n## Class\n- **OldStudent** | Name | Inbox: `old_test.msg`", encoding="utf-8")

    controller = EmailController(use_action_classifier=True)

    controller.parse_report = MagicMock(return_value=[{
        "lastname": "OldStudent",
        "class": "Class",
        "semester": "WS23",
        "path": str(mail_file),
        "folder": "Inbox"
    }])

    # Mail am 1.1.2020 (definitiv alt)
    mock_parser = mock_parser_cls.return_value
    mock_parser.get_email_date.return_value = datetime(2020, 1, 1)

    # process_all_emails mit age_months=1 ausführen
    controller.process_all_emails(source_dir, age_months=1)

    processed_report = source_dir / "processed_emails.md"
    assert processed_report.exists(), "Die Datei 'processed_emails.md' wurde nicht erstellt."

    content = processed_report.read_text(encoding="utf-8")
    assert "OldStudent" in content
    assert "Übersprungen" in content

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
@patch("mcp_university.classifier.controller.Summarizer")
def test_processed_emails_generation_legacy_mode(mock_summarizer_cls, mock_agent_cls, mock_parser_cls, tmp_path):
    """
    Testet die Berichtserstellung im Legacy-Modus (ohne Aktions-Klassifizierer).

    Dieser Test stellt sicher, dass die Berichtserstellung auch dann noch funktioniert,
    wenn 'use_action_classifier' auf False gesetzt ist, was den alten Verarbeitungsfluss
    auslöst.

    Args:
        mock_summarizer_cls (MagicMock): Mock für die Summarizer-Klasse.
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (pathlib.Path): Temporäres Verzeichnis von Pytest (Fixture).

    Returns:
        None
    """
    source_dir = tmp_path / "source_legacy"
    source_dir.mkdir()

    student_dir = source_dir / "LegacyStudent"
    inbox_dir = student_dir / "Inbox"
    inbox_dir.mkdir(parents=True)
    mail_file = inbox_dir / "legacy_test.msg"
    mail_file.write_text("dummy content")

    report_path = source_dir / "sorted_emails.md"
    report_path.write_text("# Sortierte\n\n## Class\n- **LegacyStudent** | Name | Inbox: `legacy_test.msg`", encoding="utf-8")

    controller = EmailController(use_action_classifier=False)

    controller.parse_report = MagicMock(return_value=[{
        "lastname": "LegacyStudent",
        "class": "Class",
        "semester": "WS23",
        "path": str(mail_file),
        "folder": "Inbox"
    }])

    # Mocks für die Antwortgenerierung
    mock_parser = mock_parser_cls.return_value
    mock_parser.get_email_date.return_value = datetime.now()
    mock_parser.parse.return_value = "dummy content"
    mock_parser.extract_latest_message.return_value = "dummy content"

    controller.generate_reply = MagicMock(return_value=("Betreff", "Antwort", False))
    controller.summarizer.determine_gender.return_value = "Herr"
    controller.profiler.get_profile = MagicMock(return_value=None)

    with patch("mcp_university.classifier.controller.extract_msg.openMsg"):
        controller.process_all_emails(source_dir)

    processed_report = source_dir / "processed_emails.md"
    assert processed_report.exists()
    assert "LegacyStudent" in processed_report.read_text(encoding="utf-8")
