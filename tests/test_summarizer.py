import pytest
from unittest.mock import patch
from mcp_university.summarizer.engine import Summarizer

@pytest.fixture
def mock_llm_client():
    with patch('mcp_university.summarizer.engine.LLMClientWrapper') as mock:
        yield mock

def test_answer_question(mock_llm_client):
    mock_instance = mock_llm_client.return_value
    mock_instance.chat.return_value = {
        'message': {'content': 'Die Antwort ist 42.'}
    }

    summarizer = Summarizer(model="test-model", base_url="http://test:11434")
    query = "Was ist die Antwort?"
    context = "Der Kontext enthält die Antwort 42."

    answer = summarizer.answer_question(query, context)

    assert answer == "Die Antwort ist 42."
    mock_instance.chat.assert_called_once()

    # Check if German prompts are in the call
    args, kwargs = mock_instance.chat.call_args
    system_prompt = kwargs['system_prompt']
    messages = kwargs['messages']
    assert "universitäres Wissensmanagement" in system_prompt
    assert any(query in m['content'] for m in messages)
    assert any(context in m['content'] for m in messages)

def test_summarize_email(mock_llm_client):
    mock_instance = mock_llm_client.return_value
    mock_instance.chat.return_value = {
        'message': {'content': '# E-Mail Zusammenfassung\ntest.msg'}
    }

    summarizer = Summarizer()
    summary = summarizer.summarize_file("test.msg", "Email content")

    assert "# E-Mail Zusammenfassung" in summary

    _, kwargs = mock_llm_client.return_value.chat.call_args
    assert "E-Mail Zusammenfassung" in kwargs['messages'][0]['content']

def test_summarize_long_doc(mock_llm_client):
    mock_instance = mock_llm_client.return_value
    # First call: identify type, Second call: summarize
    mock_instance.chat.side_effect = [
        {'message': {'content': 'Abschlussarbeit'}},
        {'message': {'content': '# Dokument\ntest.pdf\n# Typ\nAbschlussarbeit'}}
    ]

    summarizer = Summarizer()
    summary = summarizer.summarize_file("test.pdf", "Long document content")

    assert "Abschlussarbeit" in summary
    assert mock_instance.chat.call_count == 2

def test_answer_question_error(mock_llm_client):
    mock_instance = mock_llm_client.return_value
    mock_instance.chat.side_effect = Exception("LLM error")

    summarizer = Summarizer()
    answer = summarizer.answer_question("query", "context")

    assert answer is None
