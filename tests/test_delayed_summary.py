"""Tests for test_delayed_summary.py."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from email_classifier.controller import EmailController

@pytest.fixture
def mock_controller(tmp_path):
    """Test function docstring."""
    # Setup mock config
    mock_config = MagicMock()
    mock_config.user.emails = ["test@example.com"]
    mock_config.llm.model = "test-model"
    mock_config.llm.base_url = "http://localhost"
    mock_config.data_dir = tmp_path / "data"
    mock_config.data_dir.mkdir()

    with patch("email_classifier.controller.get_config", return_value=mock_config), \
         patch("email_classifier.controller.Summarizer"), \
         patch("email_classifier.controller.PersonProfiler"), \
         patch("email_classifier.controller.Agent"), \
         patch("email_classifier.controller.MailParser") as mock_parser_cls:

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_date.return_value = datetime.now()
        mock_parser.parse.return_value = "Parsed Email Content"

        controller = EmailController(config_path=str(tmp_path / "folders.yaml"))
        controller.summarizer.summarize_email_conversation.return_value = "# Delayed Summary Content"
        yield controller, tmp_path

def test_delayed_summary_logic(mock_controller):
    """Test function docstring."""
    controller, tmp_path = mock_controller

    # 1. Setup a "sorted" structure in a source_dir
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    student_dir = source_dir / "2024_SoSe" / "Mustermann"
    inbox = student_dir / "Inbox"
    inbox.mkdir(parents=True)

    mail_path = inbox / "20240101_100000_Test.msg"
    mail_path.write_text("dummy msg")

    # Mock parse_report to return this mail
    controller.parse_report = MagicMock(return_value=[{
        "class": "Bachelor_Thesis",
        "semester": "2024_SoSe",
        "lastname": "Mustermann",
        "folder": "Inbox",
        "path": mail_path
    }])

    # Mock class_paths
    controller.class_paths = {"Bachelor_Thesis": str(tmp_path / "archive")}

    # 2. Run process_all_emails
    # We need to mock use_action_classifier to False to enter the manual path or just check the logic
    controller.use_action_classifier = False

    # We also need to mock create_outlook_draft and generate_reply
    with patch("email_classifier.controller.create_outlook_draft", return_value=True), \
         patch.object(controller, "generate_reply", return_value=("Subject", "Reply", False)):
        controller.process_all_emails(source_dir)

    # Verify summary does NOT exist yet
    summary_file = student_dir / ".emails_summary.md"
    assert not summary_file.exists(), "Summary should NOT be created during process_all_emails"

    # 3. Run execute_action
    email_data = {
        "lastname": "Mustermann",
        "class": "Bachelor_Thesis",
        "identifier_path": student_dir
    }

    # Mock mail_parser.get_email_date for the files found in identifier_path
    controller.mail_parser.get_email_date.return_value = datetime.now()

    with patch("email_classifier.controller.create_outlook_draft", return_value=True), \
         patch.object(controller, "generate_reply", return_value=("Subject", "Reply", False)):
        # Action 0: Standard Reply
        controller.execute_action(0, mail_path, email_data)

    # Verify summary DOES exist now
    assert summary_file.exists(), "Summary should be created during execute_action"
    assert summary_file.read_text() == "# Delayed Summary Content"
