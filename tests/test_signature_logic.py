import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from email_classifier.controller import EmailController

@pytest.fixture
def controller():
    with patch("email_classifier.controller.get_config"),          patch("email_classifier.controller.Summarizer"),          patch("email_classifier.controller.PersonProfiler"),          patch("email_classifier.controller.Agent"):
        return EmailController()

def test_signature_logic_du(controller, tmp_path):
    mail_path = tmp_path / "test.msg"
    mail_path.touch()

    controller.mail_parser.parse = MagicMock(return_value="Inhalt")
    controller._detect_language = MagicMock(return_value="German")
    controller._extract_honorific_preference = MagicMock(return_value="Du")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))

    email_data = {"lastname": "Mustermann", "class": "Other"}

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.sender = "max@mustermann.de"
        with patch("email_classifier.scripts.sort_emails.extract_firstname", return_value="Max"):
            controller.execute_action(0, mail_path, email_data)

    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Abschluss: Viele Grüße, Daniel" in add_ctx

def test_signature_logic_sie(controller, tmp_path):
    mail_path = tmp_path / "test.msg"
    mail_path.touch()

    controller.mail_parser.parse = MagicMock(return_value="Inhalt")
    controller._detect_language = MagicMock(return_value="German")
    controller._extract_honorific_preference = MagicMock(return_value="Sie")
    controller.summarizer.determine_gender = MagicMock(return_value="Herr")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))

    email_data = {"lastname": "Mustermann", "class": "Other"}

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.sender = "max@mustermann.de"
        controller.execute_action(0, mail_path, email_data)

    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Abschluss: Viele Grüße, Daniel Gaida" in add_ctx
