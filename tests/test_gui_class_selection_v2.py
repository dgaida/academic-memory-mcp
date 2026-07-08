import pytest
from unittest.mock import MagicMock, patch

# Mock dependencies before import to avoid errors
with patch('mcp_university.config.get_config'),      patch('mcp_university.summarizer.engine.LLMClientWrapper'),      patch('mcp_university.summarizer.profiler.PersonProfiler'),      patch('mcp_university.parser.mail_parser.MailParser'):
    from email_classifier.controller import EmailController

@pytest.fixture
def mock_controller():
    with patch('email_classifier.controller.MailParser'),          patch('email_classifier.controller.Agent'),          patch('email_classifier.controller.MCPAgent'),          patch('email_classifier.controller.PersonProfiler'),          patch('email_classifier.controller.get_config'):
        controller = EmailController(debug=False)
        controller.summarizer = MagicMock()
        controller.summarizer.summarize_email_conversation.return_value = "Mocked Summary"
        controller.mail_parser = MagicMock()
        controller.config = MagicMock()
        controller.config.user.emails = ["test@example.com"]
        controller.config.user.name = "Test User"
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
    mock_controller.mail_parser.get_email_date.return_value = "2023-01-01"
    mock_controller._detect_language = MagicMock(return_value="German")
    mock_controller._extract_honorific_preference = MagicMock(return_value="Sie")

    # Mock generate_reply to capture arguments
    mock_controller.generate_reply = MagicMock(return_value=("Subject", "Reply", False))

    with patch("email_classifier.controller.create_outlook_draft"),          patch("email_classifier.controller.extract_msg.openMsg") as mock_open:

        mock_msg = MagicMock()
        mock_msg.sender = "student@example.com"
        mock_msg.senderName = "Student"
        mock_open.return_value.__enter__.return_value = mock_msg

        mock_controller.execute_action(0, mail_path, email_data)

    # Check if generate_reply was called with the correct email_class
    _, kwargs = mock_controller.generate_reply.call_args
    assert kwargs.get('email_class') == "NewClass"
