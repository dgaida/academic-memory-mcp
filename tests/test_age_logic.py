import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

# Ensure we can import mcp_university
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Mock dependencies to avoid import failures
with patch('mcp_university.agent.engine.SearchIndex'),      patch('mcp_university.agent.engine.MetadataStore'),      patch('mcp_university.agent.engine.ParserFactory'):
    from email_classifier.controller import EmailController

def test_age_months_suggested_action(tmp_path):
    """Checks that emails older than the specified age-months are always archived.

    Args:
        tmp_path: Pytest fixture for a temporary directory.

    Returns:
        None
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    report_path = source_dir / "sorted_emails.md"
    # Format: ## Class\n- **Student** | Subject | Inbox: `path`
    # Note: report_parser uses regex, need to make sure format is exactly what it expects
    report_path.write_text("## ClassA\n- **StudentOld** | Subj | Inbox: `dir1/mail.msg`", encoding="utf-8")

    # The parser might be looking for absolute paths or resolving them.
    # Let's check parse_report logic or just use a simple mock for it.

    with patch('email_classifier.controller.MailParser') as mock_parser_cls,          patch('email_classifier.controller.Agent'),          patch.object(EmailController, 'parse_report') as mock_parse:

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

        # Case 1: use_action_classifier = True
        controller = EmailController()
        controller.use_action_classifier = True
        emails = controller.process_all_emails(source_dir, age_months=3)

        assert len(emails) == 1
        assert emails[0]["lastname"] == "StudentOld"
        assert emails[0]["suggested_action"] == 3

        # Case 2: use_action_classifier = False
        controller.use_action_classifier = False
        emails = controller.process_all_emails(source_dir, age_months=3)

        assert len(emails) == 1
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

    with patch('email_classifier.controller.MailParser') as mock_parser_cls,          patch('email_classifier.controller.Agent'),          patch.object(EmailController, 'parse_report') as mock_parse:

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

        controller = EmailController()
        emails = controller.process_all_emails(source_dir)

        assert len(emails) == 1
        assert emails[0]["lastname"] == "StudentSent"
        assert emails[0]["suggested_action"] == 3
