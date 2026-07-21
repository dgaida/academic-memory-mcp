import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root and package path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'packages', 'email_classifier', 'src')))

from email_classifier.controller import EmailController  # noqa: E402

def test_get_suggested_action_old_email():
    """Prüft, ob alte E-Mails als 'Archivieren' (Index 3) markiert werden."""
    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'):

        mock_parser = mock_parser_cls.return_value
        # 7 Monate alt
        old_date = datetime.now() - timedelta(days=210)
        mock_parser.get_email_date.return_value = old_date

        controller = EmailController()
        mail_path = Path("test.msg")
        email_data = {"folder": "Inbox", "needs_answer": True, "lastname": "Test"}

        action = controller.get_suggested_action(mail_path, email_data, age_months=6)
        assert action == 2

def test_get_suggested_action_sent_items():
    """Prüft, ob E-Mails in SentItems als 'Archivieren' (Index 2) markiert werden."""
    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'):

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()

        controller = EmailController()
        mail_path = Path("test.msg")
        email_data = {"folder": "SentItems", "needs_answer": True, "lastname": "Test"}

        action = controller.get_suggested_action(mail_path, email_data, age_months=6)
        assert action == 2

def test_get_suggested_action_no_answer_needed():
    """Prüft, ob bereits beantwortete E-Mails als 'Archivieren' (Index 2) markiert werden."""
    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'):

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()

        controller = EmailController()
        mail_path = Path("test.msg")
        email_data = {"folder": "Inbox", "needs_answer": False, "lastname": "Test"}

        action = controller.get_suggested_action(mail_path, email_data, age_months=6)
        assert action == 2

def test_get_suggested_action_calls_classifier():
    """Prüft, ob für aktuelle Mails der Aktions-Klassifizierer aufgerufen wird."""
    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'), \
         patch.object(EmailController, 'classify_action') as mock_classify:

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()
        mock_classify.return_value = 1 # z.B. Termin vorschlagen

        controller = EmailController()
        controller.use_action_classifier = True
        mail_path = Path("test.msg")
        email_data = {"folder": "Inbox", "needs_answer": True, "lastname": "Test", "class": "TestClass"}

        action = controller.get_suggested_action(mail_path, email_data, age_months=6)
        assert action == 1
        mock_classify.assert_called_once_with(mail_path, email_class="TestClass")

def test_process_all_emails_sets_suggested_action():
    """Prüft, ob process_all_emails das suggested_action Feld für alle Mails setzt."""
    # Complete mock of EmailController initialization to avoid file system access
    with patch.object(EmailController, '__init__', lambda x, **kwargs: None):
        controller = EmailController()
        controller.use_action_classifier = True
        controller.processed_results = []
        controller.parse_report = MagicMock(return_value=[{
            "lastname": "Student",
            "class": "ClassA",
            "semester": "WS2023",
            "path": "mail.msg",
            "folder": "Inbox"
        }])
        controller.mail_parser = MagicMock()
        controller.mail_parser.get_email_date.return_value = datetime.now()
        controller.get_suggested_action = MagicMock(return_value=2)

        # We need to mock Path.rglob because process_all_emails calls it
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [Path("mail.msg")]

            emails = controller.process_all_emails(Path("."))
            assert len(emails) == 1
            assert emails[0]["suggested_action"] == 2
            controller.get_suggested_action.assert_called_once()

def test_get_suggested_action_sent_items_explicit():
    """Prüft explizit die SentItems Logik."""
    with patch('email_classifier.controller.MailParser') as mock_parser_cls,          patch('email_classifier.controller.Agent'),          patch('email_classifier.controller.PersonProfiler'):

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()

        controller = EmailController()
        mail_path = Path("some/path/test.msg")

        # Test case: folder is SentItems
        email_data = {"folder": "SentItems", "lastname": "Tester"}
        action = controller.get_suggested_action(mail_path, email_data)
        assert action == 2

        # Test case: folder is Inbox, should call classifier or default to 0
        email_data = {"folder": "Inbox", "lastname": "Tester"}
        controller.use_action_classifier = False
        action = controller.get_suggested_action(mail_path, email_data)
        assert action == 0

def test_get_suggested_action_inbox_older_than_n_months() -> None:
    """Garantiert, dass eine E-Mail im Posteingang (Inbox), die älter als N Monate ist,

    ausschließlich die Option '3) E-Mail nur archivieren.' (Index 2) vorausgewählt bekommt.

    Args:
        None

    Returns:
        None
    """
    with patch('email_classifier.controller.MailParser') as mock_parser_cls, \
         patch('email_classifier.controller.Agent'), \
         patch('email_classifier.controller.PersonProfiler'):

        mock_parser = mock_parser_cls.return_value
        # 10 Monate alt (mehr als die im Test übergebenen 6 Monate)
        old_date = datetime.now() - timedelta(days=300)
        mock_parser.get_email_date.return_value = old_date

        controller = EmailController()
        mail_path = Path("old_inbox_mail.msg")
        email_data = {"folder": "Inbox", "needs_answer": True, "lastname": "Mustermann"}

        action_idx = controller.get_suggested_action(mail_path, email_data, age_months=6)

        # Sicherstellen, dass Index 2 zurückgegeben wird
        assert action_idx == 2

        # Sicherstellen, dass dies exakt der Option "3) E-Mail nur archivieren." entspricht
        assert controller.ACTION_OPTIONS[action_idx] == "3) E-Mail nur archivieren."
