"""Tests für die Alters-Logik beim Verarbeiten von E-Mails."""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path
from typing import Any, List, Optional

# Ensure we can import mcp_university
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies to avoid import failures
with patch('mcp_university.agent.engine.SearchIndex'),      patch('mcp_university.agent.engine.MetadataStore'),      patch('mcp_university.agent.engine.ParserFactory'):
    from mcp_university.classifier.controller import EmailController

def test_age_months_suggested_action(tmp_path: Path) -> None:
    """Überprüft, dass E-Mails älter als X Monate immer archiviert werden.

    Args:
        tmp_path: Pytest fixture für ein temporäres Verzeichnis.
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    report_path = source_dir / "sorted_emails.md"
    report_path.write_text("## ClassA\n- **StudentOld** | Subj | Inbox: `dir1/mail.msg`", encoding="utf-8")

    with patch('mcp_university.classifier.controller.MailParser') as mock_parser_cls,           patch('mcp_university.classifier.controller.Agent'),           patch.object(EmailController, 'parse_report') as mock_parse:

        mock_parse.return_value = [{
            "lastname": "StudentOld",
            "class": "ClassA",
            "semester": "WS2023",
            "path": str(source_dir / "dir1/mail.msg"),
            "folder": "Inbox"
        }]

        mock_parser = mock_parser_cls.return_value
        old_date = datetime.now() - timedelta(days=185)
        mock_parser.get_email_date.return_value = old_date

        mail_dir = source_dir / "dir1"
        mail_dir.mkdir(parents=True)
        mail_path = mail_dir / "mail.msg"
        mail_path.write_text("dummy")

        controller = EmailController()
        controller.use_action_classifier = True
        emails = controller.process_all_emails(source_dir, age_months=3)

        assert len(emails) == 1
        assert emails[0]["lastname"] == "StudentOld"
        assert emails[0]["suggested_action"] == 3

        controller.use_action_classifier = False
        emails = controller.process_all_emails(source_dir, age_months=3)

        assert len(emails) == 1
        assert emails[0]["suggested_action"] == 3

def test_sent_items_suggested_action(tmp_path: Path) -> None:
    """Überprüft, dass E-Mails in SentItems immer archiviert werden.

    Args:
        tmp_path: Pytest fixture für ein temporäres Verzeichnis.
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    with patch('mcp_university.classifier.controller.MailParser') as mock_parser_cls,           patch('mcp_university.classifier.controller.Agent'),           patch.object(EmailController, 'parse_report') as mock_parse:

        mock_parse.return_value = [{
            "lastname": "StudentSent",
            "class": "ClassA",
            "semester": "WS2023",
            "path": str(source_dir / "dir1/mail.msg"),
            "folder": "SentItems"
        }]

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()

        mail_dir = source_dir / "dir1"
        mail_dir.mkdir(parents=True)
        mail_path = mail_dir / "mail.msg"
        mail_path.write_text("dummy")

        controller = EmailController()
        emails = controller.process_all_emails(source_dir)

        assert len(emails) == 1
        assert emails[0]["lastname"] == "StudentSent"
        assert emails[0]["suggested_action"] == 3
