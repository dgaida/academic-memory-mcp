"""Tests für die benutzerdefinierte Antwortlogik."""
import pytest
from unittest.mock import MagicMock, patch

from email_classifier.controller import EmailController

@pytest.fixture
def controller():
    """Erstellt einen EmailController mit gemockten Abhängigkeiten.

    Returns:
        EmailController: Der initialisierte Controller.
    """
    with patch("email_classifier.controller.get_config"),          patch("email_classifier.controller.Summarizer"),          patch("email_classifier.controller.PersonProfiler"),          patch("email_classifier.controller.Agent"):
        return EmailController()

def test_extract_honorific_preference(controller):
    """Testet die Extraktion der Anredepräferenz.

    Args:
        controller: Der Test-Controller.
    """
    # Test Du
    assert controller._extract_honorific_preference("Bevorzugte Anrede: Du") == "Du"
    assert controller._extract_honorific_preference("Man duzt sich mit dieser Person.") == "Du"
    assert controller._extract_honorific_preference("Anrede: Du") == "Du"
    
    # Test Sie (default)
    assert controller._extract_honorific_preference("Bevorzugte Anrede: Sie") == "Sie"
    assert controller._extract_honorific_preference(None) == "Sie"
    assert controller._extract_honorific_preference("") == "Sie"
    assert controller._extract_honorific_preference("Random profile text") == "Sie"

def test_detect_language_german(controller):
    """Testet die Spracherkennung für Deutsch.

    Args:
        controller: Der Test-Controller.
    """
    controller.summarizer.client.chat.return_value = {"message": {"content": "German"}}
    assert controller._detect_language("Dies ist eine deutsche E-Mail.") == "German"

def test_detect_language_english(controller):
    """Testet die Spracherkennung für Englisch.

    Args:
        controller: Der Test-Controller.
    """
    controller.summarizer.client.chat.return_value = {"message": {"content": "English"}}
    assert controller._detect_language("This is an English email.") == "English"

def test_salutation_logic_german_sie(controller, tmp_path):
    """Testet die Anredelogik für Deutsch (Sie).

    Args:
        controller: Der Test-Controller.
        tmp_path: Temporärer Pfad.
    """
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
    assert "Anrede: Guten Tag Herr Mustermann" in add_ctx
    assert kwargs["detected_language"] == "German"
    assert kwargs["honorific"] == "Sie"

def test_salutation_logic_english_du(controller, tmp_path):
    """Testet die Anredelogik für Englisch (Du).

    Args:
        controller: Der Test-Controller.
        tmp_path: Temporärer Pfad.
    """
    mail_path = tmp_path / "test.msg"
    mail_path.touch()
    
    controller.mail_parser.parse = MagicMock(return_value="Content")
    controller._detect_language = MagicMock(return_value="English")
    controller._extract_honorific_preference = MagicMock(return_value="Du")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))
    
    email_data = {"lastname": "Mustermann", "class": "Other"}
    
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.sender = "max@mustermann.de"
        with patch("email_classifier.sort_emails.extract_firstname", return_value="Max"):
            controller.execute_action(0, mail_path, email_data)
    
    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Anrede: Hi Max" in add_ctx
    assert kwargs["detected_language"] == "English"
    assert kwargs["honorific"] == "Du"

def test_salutation_logic_english_sie(controller, tmp_path):
    """Testet die Anredelogik für Englisch (Sie).

    Args:
        controller: Der Test-Controller.
        tmp_path: Temporärer Pfad.
    """
    mail_path = tmp_path / "test.msg"
    mail_path.touch()
    
    controller.mail_parser.parse = MagicMock(return_value="Content")
    controller._detect_language = MagicMock(return_value="English")
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
    assert "Anrede: Dear Mr. Mustermann" in add_ctx
    assert kwargs["detected_language"] == "English"
    assert kwargs["honorific"] == "Sie"
