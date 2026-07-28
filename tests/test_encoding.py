"""Tests for MIME decoding utility in mcp_university/utils/encoding.py."""

import pytest
import email.header
from unittest.mock import patch
from mcp_university.utils.encoding import decode_mime_header

def test_decode_mime_header_none_or_not_string() -> None:
    """Test that non-string and None inputs are returned unchanged."""
    assert decode_mime_header(None) is None
    assert decode_mime_header(123) == 123

def test_decode_mime_header_bytes_decoding() -> None:
    """Test decoding with bytes and custom encoding or fallback utf-8."""
    # Custom encoding
    s_iso = email.header.Header("Test-Öäü", "iso-8859-1").encode()
    assert "Test-Öäü" in decode_mime_header(s_iso)

    # Empty/None encoding fallback
    # We can patch email.header.decode_header to return part with None encoding
    with patch("email.header.decode_header", return_value=[(b"Fallback-Test", None)]):
        assert decode_mime_header("some_header") == "Fallback-Test"

def test_decode_mime_header_exception_handling() -> None:
    """Test fallback when exception is raised during header decoding."""
    with patch("email.header.decode_header", side_effect=Exception("Decode failed")):
        assert decode_mime_header("some_header") == "some_header"
