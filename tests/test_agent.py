import pytest
from unittest.mock import MagicMock, patch

from mcp_university.agent import Agent

@pytest.fixture
def agent(mock_llm_client_wrapper):
    with patch('mcp_university.agent.engine.ParserFactory'),          patch('mcp_university.agent.engine.MetadataStore'),          patch('mcp_university.agent.engine.SearchIndex'):
        return Agent(model="test-model", base_url="http://test-url")

def test_agent_initialization(agent):
    assert agent.model == "test-model"

def test_agent_chat_no_tools(agent, mock_llm_client_wrapper):
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Hello!'}
    }
    response = agent.chat([{'role': 'user', 'content': 'Hi'}])
    assert response == 'Hello!'

def test_agent_chat_with_tool_call(agent, mock_llm_client_wrapper):
    mock_response_1 = {
        'message': {
            'role': 'assistant',
            'tool_calls': [{
                'id': 'call_1',
                'function': {
                    'name': 'read_file',
                    'arguments': {'path': 'test.txt'}
                }
            }]
        }
    }
    mock_response_2 = {
        'message': {
            'role': 'assistant',
            'content': 'The content is: Hello'
        }
    }

    mock_llm_client_wrapper.chat.side_effect = [mock_response_1, mock_response_2]
    agent._tool_read_file = MagicMock(return_value="Hello")
    agent.available_tools["read_file"] = agent._tool_read_file

    response = agent.chat([{'role': 'user', 'content': 'Read test.txt'}])
    assert response == 'The content is: Hello'

def test_tool_read_file(agent):
    with patch.object(agent.parser_factory, 'parse', return_value="File content"):
        with patch('pathlib.Path.exists', return_value=True):
            result = agent._tool_read_file("some_path.txt")
            assert result == "File content"
