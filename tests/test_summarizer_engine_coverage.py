"""Tests to maximize coverage for engine.py (Summarizer).

This module provides unit tests targeting previously uncovered lines and edge cases
in the Summarizer class.
"""

import pytest
from unittest.mock import MagicMock, patch

from mcp_university.summarizer.engine import Summarizer


def test_summarize_short_document_fallback(mock_llm_client_wrapper: MagicMock) -> None:
    """Test summarize_file with a short document (e.g. .txt) calling _summarize_short_doc.

    Args:
        mock_llm_client_wrapper: Mocked LLM client fixture.

    Returns:
        None
    """
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': '# Short Doc Summary'}
    }

    # Suffix is .txt, which is not .msg/.eml/.pdf/.docx -> calls _summarize_short_doc
    res = summarizer.summarize_file("test.txt", "Some short text content")
    assert res == "# Short Doc Summary"
    # Verify the correct prompt or text was sent
    called_user_prompt = mock_llm_client_wrapper.chat.call_args[1]["messages"][0]["content"]
    assert "Erstelle eine strukturierte Zusammenfassung" in called_user_prompt
    assert "test.txt" in called_user_prompt


def test_chat_request_memory_error(mock_llm_client_wrapper: MagicMock) -> None:
    """Test _chat_request exception handling specifically with "memory" in the exception message.

    Args:
        mock_llm_client_wrapper: Mocked LLM client fixture.

    Returns:
        None
    """
    summarizer = Summarizer()
    # Raise exception containing "out of memory"
    mock_llm_client_wrapper.chat.side_effect = Exception("CUDA out of memory error")

    res = summarizer._chat_request("sys prompt", "user prompt")
    assert res is None


def test_summarize_folder(mock_llm_client_wrapper: MagicMock) -> None:
    """Test summarize_folder creates aggregates folder summaries.

    Args:
        mock_llm_client_wrapper: Mocked LLM client fixture.

    Returns:
        None
    """
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': '# Folder Summary'}
    }

    res = summarizer.summarize_folder("Semester_1", ["File 1 summary", "File 2 summary"])
    assert res == "# Folder Summary"
    called_user_prompt = mock_llm_client_wrapper.chat.call_args[1]["messages"][0]["content"]
    assert "Semester_1" in called_user_prompt
    assert "File 1 summary" in called_user_prompt


def test_summarize_email_conversation(mock_llm_client_wrapper: MagicMock) -> None:
    """Test summarize_email_conversation enlists the correct context and prompt.

    Args:
        mock_llm_client_wrapper: Mocked LLM client fixture.

    Returns:
        None
    """
    summarizer = Summarizer()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': '# Conversation Summary'}
    }

    res = summarizer.summarize_email_conversation("Inbox/Student_A", "Email 1\nEmail 2")
    assert res == "# Conversation Summary"
    called_user_prompt = mock_llm_client_wrapper.chat.call_args[1]["messages"][0]["content"]
    assert "Inbox/Student_A" in called_user_prompt
    assert "Email 1" in called_user_prompt


def test_determine_gender_variations(mock_llm_client_wrapper: MagicMock) -> None:
    """Test determine_gender handling different LLM outputs and None values.

    Args:
        mock_llm_client_wrapper: Mocked LLM client fixture.

    Returns:
        None
    """
    summarizer = Summarizer()

    # Case 1: LLM returns None (res is None)
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': None}
    }
    assert summarizer.determine_gender("Alex") == "Herr/Frau"

    # Case 2: LLM returns Frau
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': "  Frau. "}
    }
    assert summarizer.determine_gender("Anna") == "Frau"

    # Case 3: LLM returns BOTH Herr and Frau (e.g., "Herr/Frau" or "Frau und Herr") -> returns "Herr/Frau" (line 252)
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': "Frau und Herr"}
    }
    assert summarizer.determine_gender("Taylor") == "Herr/Frau"

    # Case 4: LLM returns an unknown word/something non-explicit
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'content': "Unbestimmt"}
    }
    assert summarizer.determine_gender("Taylor") == "Herr/Frau"
