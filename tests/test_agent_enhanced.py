"""Tests for test_agent_enhanced.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent.engine import Agent

@pytest.fixture
def mock_agent_deps():
    """Test function docstring."""
    with patch('mcp_university.agent.engine.ParserFactory'),          patch('mcp_university.agent.engine.MetadataStore'),          patch('mcp_university.agent.engine.SearchIndex'),          patch('mcp_university.agent.engine.get_config') as mock_get_config,          patch('mcp_university.agent.engine.LLMClientWrapper') as mock_llm_class:

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_cfg.user.email = "me@example.com"
        mock_cfg.calendar.send_invitations_automatically = True
        mock_get_config.return_value = mock_cfg

        mock_llm = mock_llm_class.return_value

        yield {
            'llm': mock_llm,
            'cfg': mock_cfg
        }

def test_agent_tool_get_student_info(mock_agent_deps):
    """Test function docstring."""
    agent = Agent()
    mock_conn = agent.store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value

    mock_cursor.fetchone.return_value = (1, "Max", "max@test.de", "Topic", "Active", 10, "/path")

    result = agent._tool_get_student_info("Max")
    assert "Max" in result
    assert "Topic" in result

def test_agent_tool_manage_calendar_appointment_busy(mock_agent_deps):
    """Test function docstring."""
    agent = Agent()
    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_ns.Accounts.Count = 1
        mock_ns.Accounts.Item.return_value = mock_account

        mock_folder = MagicMock()
        mock_folder.Name = "Kalender (Nur dieser Computer)"

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_root.Folders.Count = 1
        mock_root.Folders.Item.return_value = mock_folder

        mock_items = MagicMock()
        mock_folder.Items = mock_items

        mock_item = MagicMock()
        mock_item.AllDayEvent = False

        mock_restricted = MagicMock()
        mock_items.Restrict.return_value = mock_restricted
        mock_restricted.__iter__.return_value = iter([mock_item])

        result = agent._tool_manage_calendar_appointment("2024-10-01 10:00", "2024-10-01 11:00", "Meeting", "student@test.de")
        assert "belegt" in result

def test_agent_chat_tool_error_handling(mock_agent_deps):
    """Test function docstring."""
    agent = Agent()
    mock_llm = mock_agent_deps['llm']

    mock_llm.chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {'name': 'read_file', 'arguments': {'path': 'fail.txt'}}
                }]
            }
        },
        {'message': {'role': 'assistant', 'content': 'Final answer'}}
    ]

    with patch.object(agent, '_tool_read_file', side_effect=TypeError("Wrong args")):
        agent.available_tools["read_file"] = agent._tool_read_file
        agent.chat([{'role': 'user', 'content': 'read fail.txt'}])

    assert "Falsche Argumente" in str(agent.last_tool_error)
