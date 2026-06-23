"""Tests for test_mail_parser_extended.py."""
import pytest
from unittest.mock import patch
from mcp_university.parser.mail_parser import MailParser
from datetime import datetime

@pytest.fixture
def mail_parser():
    """Test function."""
    return MailParser()

def test_get_email_date(mail_parser, tmp_path):
    """Tests test_get_email_date."""
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.date = datetime(2024, 1, 1)
        
        test_mail = tmp_path / "test.msg"
        test_mail.touch()
        
        date = mail_parser.get_email_date(test_mail)
        assert date.year == 2024

def test_get_email_details_eml(mail_parser, tmp_path):
    """Tests test_get_email_details_eml."""
    eml_content = """Date: Mon, 1 Jan 2024 10:00:00 +0000
From: sender@example.com
To: recipient@example.com
Subject: Test Subject

This is the body."""
    
    test_eml = tmp_path / "test.eml"
    test_eml.write_text(eml_content)
    
    details = mail_parser.get_email_details(test_eml)
    assert details['subject'] == "Test Subject"
    assert 'from_email' in details
    assert details['from_email'] == 'sender@example.com'

@patch("extract_msg.openMsg")
def test_get_email_details_msg(mock_open, mail_parser, tmp_path):
    """Tests test_get_email_details_msg."""
    mock_msg = mock_open.return_value.__enter__.return_value
    mock_msg.subject = "MSG Subject"
    mock_msg.sender = "sender@example.com"
    mock_msg.to = "recipient@example.com"
    mock_msg.body = "Body content"
    mock_msg.attachments = []
    
    test_msg = tmp_path / "test.msg"
    test_msg.touch()
    
    details = mail_parser.get_email_details(test_msg)
    assert str(details['subject']) == "MSG Subject"

def test_parse_eml_minimal(mail_parser, tmp_path):
    """Tests test_parse_eml_minimal."""
    eml_path = tmp_path / "test.eml"
    eml_path.write_text("Subject: T\n\nContent")
    content = mail_parser.parse(eml_path)
    assert "Content" in content
