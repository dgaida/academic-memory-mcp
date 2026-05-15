import pytest
from unittest.mock import patch
from mcp_university.summarizer.engine import Summarizer

@pytest.fixture
def mock_ollama_client():
    with patch('ollama.Client') as mock:
        yield mock

def test_answer_question(mock_ollama_client):
    mock_instance = mock_ollama_client.return_value
    mock_instance.chat.return_value = {
        'message': {'content': 'The answer is 42.'}
    }

    summarizer = Summarizer(model="test-model", base_url="http://test:11434")
    query = "What is the answer?"
    context = "The context contains the answer 42."

    answer = summarizer.answer_question(query, context)

    assert answer == "The answer is 42."
    mock_instance.chat.assert_called_once()

    # Check if prompts are in the call
    args, kwargs = mock_instance.chat.call_args
    messages = kwargs['messages']
    assert any("university knowledge management assistant" in m['content'] for m in messages)
    assert any(query in m['content'] for m in messages)
    assert any(context in m['content'] for m in messages)

def test_answer_question_error(mock_ollama_client):
    mock_instance = mock_ollama_client.return_value
    mock_instance.chat.side_effect = Exception("Ollama error")

    summarizer = Summarizer()
    answer = summarizer.answer_question("query", "context")

    assert answer is None
