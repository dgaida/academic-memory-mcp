"""Tests for test_anonymizer_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.utils.anonymizer import anonymize_th_koeln_names, Anonymizer

@pytest.fixture
def mock_cfg_anonymizer():
    """Test function."""
    with patch('mcp_university.utils.anonymizer.get_config') as mock_get_config:
        mock_cfg = MagicMock()
        mock_cfg.user.email = "prof.dr.huber@th-koeln.de"
        mock_cfg.user.name = "Prof. Dr. Huber"
        mock_get_config.return_value = mock_cfg
        yield mock_cfg

def test_anonymize_th_koeln_names_empty():
    """Test function."""
    assert anonymize_th_koeln_names("") == ""
    assert anonymize_th_koeln_names(None) is None

def test_anonymize_th_koeln_names_various(mock_cfg_anonymizer):
    """Test function."""
    text = "Hallo erika.mustermann@th-koeln.de. Erika ist hier."
    anonymized = anonymize_th_koeln_names(text)
    assert "max.mustermann@th-koeln.de" in anonymized
    assert "Max Mustermann" in anonymized

def test_anonymize_th_koeln_names_user_skip(mock_cfg_anonymizer):
    """Test function."""
    text = "Von prof.dr.huber@th-koeln.de an student@smail.th-koeln.de"
    anonymized = anonymize_th_koeln_names(text)
    assert "prof.dr.huber@th-koeln.de" in anonymized
    assert "max.mustermann@smail.th-koeln.de" in anonymized

def test_anonymizer_fallback(mock_cfg_anonymizer):
    """Test function."""
    with patch('mcp_university.utils.anonymizer.LLMClientWrapper') as mock_llm_class:
        mock_llm = mock_llm_class.return_value
        mock_llm.chat.side_effect = Exception("LLM Error")
        
        anonymizer = Anonymizer()
        result = anonymizer.anonymize("Hello Max and Meli", "Max", "max@test.de", "Meli", "meli@test.de")
        
        assert "Max Mustermann" in result
        assert "Melanie Musterfrau" in result

def test_deanonymize_text_no_mapping():
    """Test function."""
    anonymizer = Anonymizer()
    assert anonymizer.deanonymize_text("Hello") == "Hello"

def test_deanonymize_args():
    """Test function."""
    anonymizer = Anonymizer()
    anonymizer.mapping = {"Max": "Original Max"}
    
    args = {"name": "Max", "count": 1}
    deanonymized = anonymizer.deanonymize_args(args)
    
    assert deanonymized["name"] == "Original Max"
    assert deanonymized["count"] == 1

def test_deanonymize_args_no_mapping():
    """Test function."""
    anonymizer = Anonymizer()
    args = {"name": "Max"}
    assert anonymizer.deanonymize_args(args) == args
