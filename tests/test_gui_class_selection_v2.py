import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Mock dependencies before import to avoid errors
with patch('mcp_university.config.get_config'),      patch('mcp_university.summarizer.engine.LLMClientWrapper'),      patch('mcp_university.summarizer.profiler.PersonProfiler'),      patch('mcp_university.parser.mail_parser.MailParser'):
    from email_classifier.controller import EmailController

@pytest.fixture
def mock_controller():
    with patch('email_classifier.controller.MailParser'),          patch('email_classifier.controller.Agent'),          patch('email_classifier.controller.MCPAgent'),          patch('email_classifier.controller.PersonProfiler'),          patch('email_classifier.controller.get_config'):
        controller = EmailController(debug=False)
        controller.summarizer = MagicMock()
        controller.mail_parser = MagicMock()
        return controller

def test_execute_action_respects_new_class(mock_controller, tmp_path):
    """Verifies that execute_action uses new_class from email_data."""
    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy content")

    email_data = {
        "class": "OldClass",
        "new_class": "NewClass",
        "lastname": "Test",
        "identifier_path": tmp_path
    }

    mock_controller.mail_parser.parse.return_value = "Email Body"
    mock_controller.mail_parser.extract_latest_message.return_value = "Email Body"
    mock_controller._detect_language = MagicMock(return_value="German")
    mock_controller._extract_honorific_preference = MagicMock(return_value="Sie")

    # Mock generate_reply to capture arguments
    mock_controller.generate_reply = MagicMock(return_value=("Subject", "Reply", False))

    mock_controller.execute_action(0, mail_path, email_data)

    # Check if generate_reply was called with the correct email_class
    _, kwargs = mock_controller.generate_reply.call_args
    assert kwargs.get('email_class') == "NewClass"

    # Check if skill_path was derived from NewClass
    # The skill_path logic uses NewClass if present.
