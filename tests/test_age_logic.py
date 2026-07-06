import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Ensure we can import mcp_university and email_classifier
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'packages', 'email_classifier', 'src')))

from email_classifier.controller import EmailController  # noqa: E402

def test_age_months_suggested_action(tmp_path):
    """Checks that emails older than the specified age-months are always archived.

    Args:
        tmp_path: Pytest fixture for a temporary directory.

    Returns:
        None
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'), \
         patch.object(EmailController, '__init__', lambda x, **kwargs: None), \
         patch.object(EmailController, 'parse_report') as mock_parse:

        # Manually return the email dict that parse_report would produce
        mock_parse.return_value = [{
            "lastname": "StudentOld",
            "class": "ClassA",
            "semester": "WS2023",
            "path": str(source_dir / "dir1/mail.msg"),
            "folder": "Inbox"
        }]

        mock_parser = mock_parser_cls.return_value
        # 6 months ago
        old_date = datetime.now() - timedelta(days=185)
        mock_parser.get_email_date.return_value = old_date

        # Create dummy mail file
        mail_dir = source_dir / "dir1"
        mail_dir.mkdir(parents=True)
        mail_path = mail_dir / "mail.msg"
        mail_path.write_text("dummy")

        # Mock rglob to find the mail
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [mail_path]

            controller = EmailController()
            controller.use_action_classifier = True
            controller.processed_results = []
            controller.mail_parser = mock_parser

            emails = controller.process_all_emails(source_dir, age_months=3)

            assert len(emails) == 1
            assert emails[0]["lastname"] == "StudentOld"
            assert emails[0]["suggested_action"] == 3

def test_sent_items_suggested_action(tmp_path):
    """Checks that emails in SentItems are always archived.

    Args:
        tmp_path: Pytest fixture for a temporary directory.

    Returns:
        None
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'), \
         patch.object(EmailController, '__init__', lambda x, **kwargs: None), \
         patch.object(EmailController, 'parse_report') as mock_parse:

        mock_parse.return_value = [{
            "lastname": "StudentSent",
            "class": "ClassA",
            "semester": "WS2023",
            "path": str(source_dir / "dir1/mail.msg"),
            "folder": "SentItems"
        }]

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()

        # Create dummy mail file
        mail_dir = source_dir / "dir1"
        mail_dir.mkdir(parents=True)
        mail_path = mail_dir / "mail.msg"
        mail_path.write_text("dummy")

        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [mail_path]

            controller = EmailController()
            controller.use_action_classifier = True
            controller.processed_results = []
            controller.mail_parser = mock_parser

            emails = controller.process_all_emails(source_dir)

            assert len(emails) == 1
            assert emails[0]["lastname"] == "StudentSent"
            assert emails[0]["suggested_action"] == 3
