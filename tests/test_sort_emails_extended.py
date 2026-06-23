"""Tests for test_sort_emails_extended.py."""
import pytest
from mcp_university.classifier.sort_emails import extract_lastname

def test_extract_lastname_edge_cases():
    """Test function docstring."""
    assert extract_lastname("") == "Unknown"
    assert extract_lastname("(No Sender)") == "Unknown"
    # Rule: if dot in local part, take part AFTER dot
    assert extract_lastname("max.mustermann@smail.th-koeln.de") == "Mustermann"
    # Max Mustermann <...> -> Display name rule: take last word
    assert extract_lastname("Max Mustermann <max@test.com>") == "Mustermann"
    # Mustermann, Max -> Display name rule: take first part before comma
    assert extract_lastname("Mustermann, Max") == "Mustermann"
    # 'Quoted Name' -> Display name rule
    assert extract_lastname("'Quoted Name'") == "Name"

def test_extract_lastname_smail_complex():
    """Test function docstring."""
    # local_part without dot -> take all
    assert extract_lastname("mmustermann@smail.th-koeln.de") == "Mmustermann"
    # local_part with dot -> take after first dot
    assert extract_lastname("erika.mustermann@th-koeln.de") == "Mustermann"
