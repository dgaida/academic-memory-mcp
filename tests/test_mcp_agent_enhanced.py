"""Tests for test_mcp_agent_enhanced.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent.mcp_agent import MCPAgent

@pytest.fixture
def mock_dependencies():
    """Test function."""
    with patch('mcp_university.mcp_server.tool_server.create_tool_server') as mock_create_server,          patch('mcp_university.agent.mcp_agent.LLMClientWrapper') as mock_llm_class,          patch('mcp_university.agent.mcp_agent.Anonymizer') as mock_anon_class,          patch('mcp_university.agent.mcp_agent.get_config') as mock_get_config:
        
        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_get_config.return_value = mock_cfg
        
        mock_server = MagicMock()
        mock_tool_comp = MagicMock()
        mock_tool_comp.name = "read_file"
        mock_tool_comp.fn = MagicMock(return_value="file content")
        mock_server.local_provider._components = {"tool:read_file": mock_tool_comp}
        mock_create_server.return_value = mock_server
        
        mock_llm = mock_llm_class.return_value
        
        yield {
            'server': mock_server,
            'llm': mock_llm,
            'anon': mock_anon_class.return_value,
            'tool_fn': mock_tool_comp.fn
        }

def test_mcp_agent_chat_simple(mock_dependencies):
    """Tests test_mcp_agent_chat_simple."""
    agent = MCPAgent()
    mock_dependencies['llm'].chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Hello'}
    }
    
    response = agent.chat([{'role': 'user', 'content': 'Hi'}])
    assert response == 'Hello'

def test_mcp_agent_chat_with_tool(mock_dependencies):
    """Tests test_mcp_agent_chat_with_tool."""
    agent = MCPAgent()
    
    mock_dependencies['llm'].chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {'name': 'read_file', 'arguments': {'path': 'test.txt'}}
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'The content is: file content'}
        }
    ]
    
    response = agent.chat([{'role': 'user', 'content': 'read test.txt'}])
    assert response == 'The content is: file content'

def test_mcp_agent_chat_with_anonymization(mock_dependencies):
    """Tests test_mcp_agent_chat_with_anonymization."""
    agent = MCPAgent(use_cloud=True)
    
    mock_anon = mock_dependencies['anon']
    mock_anon.anonymize.side_effect = lambda x, name, email: x.replace(name, "PERSON")
    mock_anon.deanonymize_text.side_effect = lambda x: x.replace("PERSON", "Original Name")
    mock_anon.deanonymize_args.side_effect = lambda x: x
    mock_anon.mapping = {"PERSON": "Original Name"}
    
    mock_dependencies['llm'].chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Hello PERSON'}
    }
    
    response = agent.chat([{'role': 'user', 'content': 'Hi Original Name'}], 
                          sender_name="Original Name", sender_email="orig@example.com")
    
    assert response == 'Hello Original Name'

def test_mcp_agent_tool_error(mock_dependencies):
    """Tests test_mcp_agent_tool_error."""
    agent = MCPAgent()
    mock_dependencies['tool_fn'].side_effect = Exception("Tool failed")
    
    mock_dependencies['llm'].chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {'name': 'read_file', 'arguments': {'path': 'test.txt'}}
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'Error happened'}
        }
    ]
    
    agent.chat([{'role': 'user', 'content': 'read test.txt'}])
    assert "Tool failed" in str(agent.last_tool_error)
