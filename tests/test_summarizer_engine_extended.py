"""Tests for test_summarizer_engine_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.summarizer.engine import Summarizer

@pytest.fixture
def mock_summarizer_llm():
    """Test function docstring."""
    with patch('mcp_university.summarizer.engine.LLMClientWrapper') as mock_llm_class:
        mock_llm = mock_llm_class.return_value
        mock_llm.model = "test-model"
        yield mock_llm

def test_summarizer_chat_request_success(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.return_value = {"message": {"content": "Response"}}
    res = summarizer._chat_request("sys", "user")
    assert res == "Response"

def test_summarizer_chat_request_fail(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.side_effect = Exception("Fail")
    res = summarizer._chat_request("sys", "user")
    assert res is None

def test_summarizer_identify_doc_type(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.return_value = {"message": {"content": " Protokoll "}}
    res = summarizer._identify_document_type("Some content")
    assert res == "Protokoll"

def test_summarizer_identify_doc_type_none(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.return_value = {"message": {"content": ""}}
    res = summarizer._identify_document_type("Some content")
    assert res == "Unbekannt"

def test_summarizer_determine_gender_fallback(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.return_value = None
    res = summarizer.determine_gender("Alex")
    assert res == "Herr/Frau"

def test_summarizer_determine_gender_success(mock_summarizer_llm):
    """Test function docstring."""
    summarizer = Summarizer()
    mock_summarizer_llm.chat.return_value = {"message": {"content": " Herr "}}
    res = summarizer.determine_gender("Max")
    assert res == "Herr"
