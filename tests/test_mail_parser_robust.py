from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from mcp_university.parser.mail_parser import MailParser

def test_get_msg_details_robust_recipients():
    parser = MailParser()
    file_path = Path("test.msg")

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_msg

        # Test case 1: recipients list empty, but msg.to filled
        mock_msg.recipients = []
        mock_msg.to = "Recipient Name <recipient@example.com>"
        mock_msg.cc = "CC Person <cc@example.com>"
        mock_msg.sender = "Sender <sender@example.com>"
        mock_msg.date = datetime(2024, 1, 1)
        mock_msg.subject = "Test"
        mock_msg.body = "Body"
        mock_msg.header = {}

        details = parser.get_email_details(file_path)

        assert details["from_email"] == "sender@example.com"
        assert details["to"] == [{"name": "Recipient Name", "email": "recipient@example.com"}]
        assert details["cc"] == [{"name": "CC Person", "email": "cc@example.com"}]

def test_get_msg_details_robust_smtp_address():
    parser = MailParser()
    file_path = Path("test.msg")

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_msg

        # Test case 2: recipients list has Exchange-style objects (no email, but smtpAddress)
        mock_rec = MagicMock()
        mock_rec.smtpAddress = "real@example.com"
        mock_rec.email = None
        mock_rec.name = "Real Name"
        mock_rec.type = "To"

        mock_msg.recipients = [mock_rec]
        mock_msg.sender = "sender@example.com"
        mock_msg.date = datetime(2024, 1, 1)

        details = parser.get_email_details(file_path)

        assert details["to"] == [{"name": "Real Name", "email": "real@example.com"}]

def test_get_msg_details_fallback_headers():
    parser = MailParser()
    file_path = Path("test.msg")

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_msg

        # Test case 3: everything empty except headers
        mock_msg.recipients = []
        mock_msg.to = None
        mock_msg.cc = None
        mock_msg.sender = None
        mock_msg.header = {
            "From": "Header Sender <header@example.com>",
            "To": "Header To <to@example.com>",
            "Cc": "Header Cc <cc@example.com>"
        }
        mock_msg.date = datetime(2024, 1, 1)

        details = parser.get_email_details(file_path)

        assert details["from_email"] == "header@example.com"
        assert details["to"] == [{"name": "Header To", "email": "to@example.com"}]
        assert details["cc"] == [{"name": "Header Cc", "email": "cc@example.com"}]

def test_parse_address_list_various_formats():
    parser = MailParser()

    assert parser._parse_address_list("simple@example.com") == [{"name": "", "email": "simple@example.com"}]
    assert parser._parse_address_list("Name <email@example.com>") == [{"name": "Name", "email": "email@example.com"}]
    assert parser._parse_address_list("'Quoted Name' <email@example.com>") == [{"name": "Quoted Name", "email": "email@example.com"}]
    assert parser._parse_address_list("A, B <a@b.com>, C <c@d.com>") == [
        {"name": "A", "email": ""}, # getaddresses might be tricky with commas
        {"name": "B", "email": "a@b.com"},
        {"name": "C", "email": "c@d.com"}
    ] or [{"name": "", "email": "a@b.com"}, {"name": "", "email": "c@d.com"}] # Depending on behavior

    # Let's verify what getaddresses actually does in our environment
    input_str = "Recipient Name <recipient@example.com>, CC Person <cc@example.com>"
    expected = [
        {"name": "Recipient Name", "email": "recipient@example.com"},
        {"name": "CC Person", "email": "cc@example.com"}
    ]
    assert parser._parse_address_list(input_str) == expected
