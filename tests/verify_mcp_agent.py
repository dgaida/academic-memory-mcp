"""Tests for verify_mcp_agent.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent.mcp_agent import MCPAgent

@pytest.fixture
def mock_tool_server():
    """Test function."""
    with patch('mcp_university.mcp_server.tool_server.create_tool_server') as mock:
        mock_server = MagicMock()
        mock_server.local_provider._components = {}
        mock.return_value = mock_server
        yield mock

def test_mcp_agent_chat(mock_llm_client_wrapper, mock_tool_server):
    """Tests test_mcp_agent_chat."""
    agent = MCPAgent()
    mock_llm_client_wrapper.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'MCP Response'}
    }
    response = agent.chat([{'role': 'user', 'content': 'test'}])
    assert response == 'MCP Response'
