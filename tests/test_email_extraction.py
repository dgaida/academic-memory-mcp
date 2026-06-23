"""Tests for test_email_extraction.py."""
from mcp_university.parser.mail_parser import MailParser

def test_extract_latest_message_zitat():
    """Test function docstring."""
    parser = MailParser()
    text = "Dies ist die neue Nachricht.\n\nZitat von daniel.gaida@th-koeln.de:\n> Dies ist die alte Nachricht."
    result = parser.extract_latest_message(text)
    assert result == "Dies ist die neue Nachricht."

def test_extract_latest_message_am_schrieb():
    """Test function docstring."""
    parser = MailParser()
    text = "Hallo Daniel,\n\ndanke für die Mail.\n\nAm 22.02.2026 um 20:16 schrieb daniel.gaida@th-koeln.de:\n> Alte Nachricht"
    result = parser.extract_latest_message(text)
    assert result == "Hallo Daniel,\n\ndanke für die Mail."

def test_extract_latest_message_weitergeleitet():
    """Test function docstring."""
    parser = MailParser()
    text = "Hier ist was Neues.\n\n-------- Weitergeleitete Nachricht --------\nDatum: ..."
    result = parser.extract_latest_message(text)
    assert result == "Hier ist was Neues."

def test_extract_latest_message_from():
    """Test function docstring."""
    parser = MailParser()
    text = "Neue Info.\n\nFrom: daniel.gaida@th-koeln.de <daniel.gaida@th-koeln.de>\nSent: ..."
    result = parser.extract_latest_message(text)
    assert result == "Neue Info."

def test_extract_latest_message_quotes():
    """Test function docstring."""
    parser = MailParser()
    text = "Neu.\n\n> Quote 1\n> Quote 2"
    result = parser.extract_latest_message(text)
    assert result == "Neu."

def test_extract_latest_message_no_marker():
    """Test function docstring."""
    parser = MailParser()
    text = "Nur eine neue Nachricht ohne Historie."
    result = parser.extract_latest_message(text)
    assert result == "Nur eine neue Nachricht ohne Historie."
