from unittest.mock import patch
from pathlib import Path
from mcp_university.parser.mail_parser import MailParser
from extract_msg.exceptions import StandardViolationError

def test_parse_msg_signed_fallback():
    parser = MailParser()
    file_path = Path("signed.msg")

    with patch("extract_msg.openMsg") as mock_open:
        # Simulate StandardViolationError during context manager entry
        mock_open.side_effect = StandardViolationError("File does not contain a property stream.")

        with patch.object(parser, "_parse_eml") as mock_parse_eml:
            mock_parse_eml.return_value = "Fallback content"

            result = parser.parse(file_path)

            assert result == "Fallback content"
            mock_parse_eml.assert_called_once_with(file_path)

def test_get_msg_details_signed_fallback():
    parser = MailParser()
    file_path = Path("signed.msg")

    with patch("extract_msg.openMsg") as mock_open:
        # Simulate StandardViolationError
        mock_open.side_effect = StandardViolationError("File does not contain a property stream.")

        with patch.object(parser, "_get_eml_details") as mock_get_eml:
            mock_get_eml.return_value = {"subject": "Fallback"}

            result = parser.get_email_details(file_path)

            assert result == {"subject": "Fallback"}
            mock_get_eml.assert_called_once_with(file_path)

def test_save_msg_attachments_signed_graceful():
    parser = MailParser()
    file_path = Path("signed.msg")
    target_dir = Path("attachments")

    with patch("extract_msg.openMsg") as mock_open:
        # Simulate StandardViolationError
        mock_open.side_effect = StandardViolationError("File does not contain a property stream.")

        result = parser.save_attachments(file_path, target_dir)

        assert result == []
