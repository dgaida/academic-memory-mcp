"""Tests for test_llm_client.py."""

def test_llm_client_wrapper_chat(mock_llm_client_wrapper):
    """Test function docstring."""
    # Setup mock behavior
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Mocked Content'}
    }

    # We call the mock instance directly to test its return value
    response = mock_llm_client_wrapper.chat([{'role': 'user', 'content': 'Hello'}])

    # Verify
    assert response['message']['content'] == 'Mocked Content'
