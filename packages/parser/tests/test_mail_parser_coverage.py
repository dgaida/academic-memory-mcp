"""Tests to maximize coverage for mail_parser.py.

This module provides unit tests targeting previously uncovered lines and edge cases
in the MailParser class.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from extract_msg.exceptions import StandardViolationError

from academic_parser.mail_parser import MailParser


@pytest.fixture
def academic_parser() -> MailParser:
    """Fixture to provide a MailParser instance.

    Returns:
        MailParser: An instance of the MailParser.
    """
    return MailParser()


def test_invalid_date_filename(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_email_date when filename matches date pattern but is invalid.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    invalid_file = tmp_path / "20269999_999999 - Test.msg"
    invalid_file.touch()

    # Stub the rest to return a fixed date to ensure the code reached fallback
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.date = datetime(2026, 12, 12)
        date = academic_parser.get_email_date(invalid_file)
        assert date == datetime(2026, 12, 12)


def test_eml_date_exception_fallback(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_email_date when eml reading raises an exception.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    bad_eml = tmp_path / "corrupt.eml"
    bad_eml.write_bytes(b"\x00\x00\x00")

    # We mock open to raise exception
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        # Will fail EML open and fallback to mtime
        date = academic_parser.get_email_date(bad_eml)
        assert isinstance(date, datetime)


def test_get_email_date_mtime_exception(academic_parser: MailParser) -> None:
    """Test get_email_date when mtime stat raises an exception.

    Args:
        academic_parser: The MailParser instance.

    Returns:
        None
    """
    non_existent = Path("does_not_exist_at_all.eml")
    # This path does not exist, and we mock open/extract_msg to fail
    with patch("builtins.open", side_effect=Exception("Error")):
        date = academic_parser.get_email_date(non_existent)
        assert date == datetime.min


def test_extract_latest_message_empty(academic_parser: MailParser) -> None:
    """Test extract_latest_message when input is empty or None.

    Args:
        academic_parser: The MailParser instance.

    Returns:
        None
    """
    assert academic_parser.extract_latest_message("") == ""


def test_extract_latest_message_fallback_under_two_lines(academic_parser: MailParser) -> None:
    """Test extract_latest_message fallback logic when lines count is under 2.

    We patch text.splitlines to simulate different lengths on successive calls,
    satisfying the exact condition where did_skip_start and marker_found are
    False, extracted_lines_count < 2, and original_lines_count > extracted_lines_count.

    Args:
        academic_parser: The MailParser instance.

    Returns:
        None
    """
    class MagicString(str):
        def __init__(self, val: str) -> None:
            self.calls = 0
        def splitlines(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return ["Line 1"]
            else:
                return ["Line 1", "Line 2"]

    magic_text = MagicString("Line 1\nLine 2")
    res = academic_parser.extract_latest_message(magic_text)
    assert res == "Line 1\nLine 2"


def test_parse_msg_import_error_fallback(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test parse_msg fallback when extract_msg raises ImportError or is missing.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.write_text("Subject: Fallback\n\nFallback Body")

    with patch.dict(sys.modules, {"extract_msg": None}):
        res = academic_parser.parse(msg_path)
        assert "Fallback Body" in res


def test_parse_msg_exceptions_and_standard_violation(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test parse_msg and get_msg_details StandardViolationError fallback.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "signed.msg"
    msg_path.touch()

    # We mock extract_msg.openMsg to raise StandardViolationError
    # We first import it or define a mock one to raise
    with patch("extract_msg.openMsg", side_effect=StandardViolationError("Signed")):
        with patch.object(academic_parser, "_parse_eml", return_value="EML Fallback"):
            res = academic_parser.parse(msg_path)
            assert res == "EML Fallback"


def test_parse_msg_att_get_filename_exception(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test parse_msg when attachment.getFilename raises exception.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.subject = "Subj"
        mock_msg.sender = "Sender"
        mock_msg.date = "Date"
        mock_msg.body = "Body"

        mock_att = MagicMock()
        mock_att.getFilename.side_effect = Exception("error")
        #Fallback to name/longFilename
        mock_att.name = "fallback.txt"
        mock_msg.attachments = [mock_att]

        res = academic_parser.parse(msg_path)
        assert "fallback.txt" in res


def test_parse_eml_decode_fallback(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test parse_eml decoding fallback when UnicodeDecodeError occurs.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "bad_charset.eml"
    # EML content with non-utf8 characters
    eml_path.write_bytes(
        b"Subject: Test\n"
        b"Content-Type: text/plain; charset=utf-8\n"
        b"Content-Transfer-Encoding: 8bit\n\n"
        b"Bad bytes: \xff\xfe\xfd"
    )
    res = academic_parser.parse(eml_path)
    assert "Bad bytes" in res


def test_parse_address_list_empty_skip(academic_parser: MailParser) -> None:
    """Test parse_address_list skips empty parsed addresses.

    Args:
        academic_parser: The MailParser instance.

    Returns:
        None
    """
    # Empty string should return empty list
    assert academic_parser._parse_address_list("") == []
    # If getaddresses yields something empty
    with patch("academic_parser.mail_parser.getaddresses", return_value=[("", "")]):
        assert academic_parser._parse_address_list("some_string") == []


def test_get_msg_details_sender_raw_fallback(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_msg_details sender fallback when from_info is empty.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.sender = "raw_sender_email@test.com"
        mock_msg.recipients = []
        mock_msg.to = None
        mock_msg.cc = None
        mock_msg.header = None
        mock_msg.subject = "Subject"
        mock_msg.body = "Body"

        # Mock _parse_address_list to return empty to trigger the fallback
        with patch.object(academic_parser, "_parse_address_list", return_value=[]):
            details = academic_parser.get_email_details(msg_path)
            assert details["from_email"] == "raw_sender_email@test.com"
            assert details["from_name"] == ""


def test_get_msg_details_cc_type(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_msg_details when recipient type contains CC.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.touch()

    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        mock_msg.sender = "sender@test.com"
        mock_msg.subject = "Subject"
        mock_msg.body = "Body"
        mock_msg.header = None

        rec1 = MagicMock()
        rec1.smtpAddress = "cc_person@test.com"
        rec1.name = "CC Person"
        rec1.type = "Cc"

        mock_msg.recipients = [rec1]

        details = academic_parser.get_email_details(msg_path)
        assert details["cc"] == [{"name": "CC Person", "email": "cc_person@test.com"}]


def test_get_eml_details_date_fallback(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_eml_details when parsedate_to_datetime fails.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "test.eml"
    eml_path.write_text("Date: Invalid Date\nFrom: test@test.com\n\nBody")

    with patch("academic_parser.mail_parser.parsedate_to_datetime", side_effect=Exception("parse error")):
        details = academic_parser.get_email_details(eml_path)
        assert isinstance(details["date"], datetime)


def test_parse_addr_skip(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_eml_details parse_addr skips empty addresses.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "test.eml"
    eml_path.write_text("Date: Mon, 1 Jan 2024 10:00:00 +0000\nFrom: test@test.com\nTo: \n\nBody")

    # get_all returns list, we can stub parse_addr to receive a mock that returns empty getaddresses
    with patch("academic_parser.mail_parser.getaddresses", return_value=[("", "")]):
        details = academic_parser.get_email_details(eml_path)
        assert details["to"] == []


def test_get_eml_details_multipart_text(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test get_eml_details with multipart containing text/plain.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg = MIMEMultipart()
    msg['Subject'] = "Multipart test"
    msg['From'] = "sender@test.com"
    msg['Date'] = "Mon, 1 Jan 2024 10:00:00 +0000"

    part = MIMEText("Plain text body", "plain")
    msg.attach(part)

    eml_path = tmp_path / "multipart.eml"
    eml_path.write_bytes(msg.as_bytes())

    details = academic_parser.get_email_details(eml_path)
    assert details["body"] == "Plain text body"


def test_save_attachments_eml(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test save_attachments for .eml files.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "test.eml"
    eml_path.touch()

    with patch.object(academic_parser, "_save_eml_attachments", return_value=[Path("saved")]) as mock_save:
        res = academic_parser.save_attachments(eml_path, tmp_path)
        assert res == [Path("saved")]
        mock_save.assert_called_once_with(eml_path, tmp_path)


def test_save_msg_attachments_import_error(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _save_msg_attachments fallback when extract_msg raises StandardViolationError.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.touch()

    with patch("extract_msg.openMsg", side_effect=StandardViolationError("Signed")):
        res = academic_parser._save_msg_attachments(msg_path, tmp_path)
        assert res == []


def test_save_msg_attachments_success_and_exception(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _save_msg_attachments success path and general exception handling.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg_path = tmp_path / "test.msg"
    msg_path.touch()

    # Success Path with custom attributes
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = mock_open.return_value.__enter__.return_value
        att1 = MagicMock()
        att1.getFilename.side_effect = Exception("getFilename failed")
        att1.name = "file1.txt"
        att1.data = b"hello"
        mock_msg.attachments = [att1]

        res = academic_parser._save_msg_attachments(msg_path, tmp_path)
        assert len(res) == 1
        assert res[0].name == "file1.txt"

    # Exception Path
    with patch("extract_msg.openMsg", side_effect=Exception("General exception")):
        res = academic_parser._save_msg_attachments(msg_path, tmp_path)
        assert res == []


def test_save_eml_attachments(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _save_eml_attachments exception handling and normal execution.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "test.eml"
    # Normal execution is already tested in test_mail_attachments.py, let's test exception handling:
    with patch("builtins.open", side_effect=Exception("Read error")):
        res = academic_parser._save_eml_attachments(eml_path, tmp_path)
        assert res == []


def test_get_unique_path_loop(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _get_unique_path collision loop when final files already exist.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    base_file = tmp_path / "doc.txt"
    base_file.touch()

    final_file = tmp_path / "doc_final.txt"
    final_file.touch()

    final_file_1 = tmp_path / "doc_final_1.txt"
    final_file_1.touch()

    # _get_unique_path should return doc_final_2.txt
    res = academic_parser._get_unique_path(base_file)
    assert res.name == "doc_final_2.txt"


def test_get_eml_details_exception(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _get_eml_details when open raises an exception.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "exception.eml"
    with patch("builtins.open", side_effect=Exception("Simulated open exception")):
        details = academic_parser._get_eml_details(eml_path)
        assert details["date"] == datetime.min
        assert details["from_email"] == ""


def test_parse_eml_exception(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _parse_eml when open raises an exception.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    eml_path = tmp_path / "exception.eml"
    with patch("builtins.open", side_effect=Exception("Simulated open exception")):
        content = academic_parser._parse_eml(eml_path)
        assert content is None


def test_save_eml_attachments_success(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test _save_eml_attachments with a valid attachment.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    msg = MIMEMultipart()
    msg['Subject'] = "Attachment EML"
    msg['From'] = "sender@test.com"

    part = MIMEText("attachment content", "plain")
    part.add_header("Content-Disposition", "attachment", filename="test_attachment.txt")
    msg.attach(part)

    eml_path = tmp_path / "with_attachment.eml"
    eml_path.write_bytes(msg.as_bytes())

    res = academic_parser._save_eml_attachments(eml_path, tmp_path)
    assert len(res) == 1
    assert res[0].name == "test_attachment.txt"
    assert res[0].read_text() == "attachment content"


def test_standard_violation_error_imports(academic_parser: MailParser, tmp_path: Path) -> None:
    """Test StandardViolationError fallback import path.

    Args:
        academic_parser: The MailParser instance.
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    # StandardViolationError raises ImportError fallback class definition
    with patch.dict(sys.modules, {"extract_msg.exceptions": None}):
        with patch("extract_msg.openMsg") as mock_open:
            # Re-triggering _parse_msg imports
            mock_open.side_effect = Exception("error")
            res = academic_parser.parse(tmp_path / "dummy.msg")
            # Falls back to parse_eml
            assert res is None
