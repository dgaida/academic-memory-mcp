"""Tests for test_mail_attachments.py."""
from unittest.mock import MagicMock, patch
from academic_parser.mail_parser import MailParser
from email.message import EmailMessage

def test_parse_msg_with_attachments(tmp_path):
    """Test function docstring."""
    academic_parser = MailParser()
    msg_file = tmp_path / "test.msg"
    msg_file.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.subject = "Test Subject"
        mock_msg.sender = "sender@example.com"
        mock_msg.date = "Mon, 1 Jan 2024"
        mock_msg.body = "Body content."

        # Mock attachments
        att1 = MagicMock()
        att1.getFilename.return_value = "document.pdf"
        att2 = MagicMock()
        att2.getFilename.return_value = "image.png"
        mock_msg.attachments = [att1, att2]

        mock_open.return_value.__enter__.return_value = mock_msg

        content = academic_parser.parse(msg_file)
        assert "Subject: Test Subject" in content
        assert "Body content." in content
        assert "Anhänge:" in content
        assert "document.pdf" in content
        assert "image.png" in content

def test_parse_eml_with_attachments(tmp_path):
    """Test function docstring."""
    academic_parser = MailParser()
    eml_file = tmp_path / "test.eml"

    # Create an EML with attachments using EmailMessage
    msg = EmailMessage()
    msg['Subject'] = "EML Subject"
    msg['From'] = "sender@example.com"
    msg['Date'] = "Mon, 1 Jan 2024 10:00:00 +0000"
    msg.set_content("EML body content.")

    # Add attachments
    msg.add_attachment(b"dummy pdf content", maintype="application", subtype="pdf", filename="test.pdf")
    msg.add_attachment(b"dummy text content", maintype="text", subtype="plain", filename="notes.txt")

    eml_file.write_bytes(msg.as_bytes())

    content = academic_parser.parse(eml_file)
    assert "Subject: EML Subject" in content
    assert "EML body content." in content
    assert "Anhänge:" in content
    assert "test.pdf" in content
    assert "notes.txt" in content

def test_parse_eml_no_attachments(tmp_path):
    """Test function docstring."""
    academic_parser = MailParser()
    eml_file = tmp_path / "test_no_att.eml"

    msg = EmailMessage()
    msg['Subject'] = "No Att"
    msg['From'] = "sender@example.com"
    msg.set_content("No attachments here.")

    eml_file.write_bytes(msg.as_bytes())

    content = academic_parser.parse(eml_file)
    assert "Subject: No Att" in content
    assert "Anhänge:" not in content
