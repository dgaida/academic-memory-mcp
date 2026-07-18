"""Comprehensive coverage boost tests for MCPAgent in mcp_university/agent/mcp_agent.py."""

import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent.mcp_agent import MCPAgent


@pytest.fixture
def mock_mcp_agent_deps():
    """Sets up mocks for get_config, LLMClientWrapper, Anonymizer, and Tool Server.

    Yields:
        dict: A dictionary of mocked components.
    """
    with patch('mcp_university.mcp_server.tool_server.create_tool_server') as mock_create_server, \
         patch('mcp_university.agent.mcp_agent.LLMClientWrapper') as mock_llm_class, \
         patch('mcp_university.agent.mcp_agent.Anonymizer') as mock_anon_class, \
         patch('mcp_university.agent.mcp_agent.get_config') as mock_get_config:

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "local-model"
        mock_cfg.llm.base_url = "http://localhost:11434"
        mock_get_config.return_value = mock_cfg

        mock_server = MagicMock()
        mock_tool_comp = MagicMock()
        mock_tool_comp.name = "read_file"
        mock_tool_comp.fn = MagicMock(return_value="file content")

        mock_appointment_comp = MagicMock()
        mock_appointment_comp.name = "manage_calendar_appointment"
        mock_appointment_comp.fn = MagicMock(return_value="ERFOLG: Termin eingetragen")

        mock_server.local_provider._components = {
            "tool:read_file": mock_tool_comp,
            "tool:manage_calendar_appointment": mock_appointment_comp
        }
        mock_create_server.return_value = mock_server

        mock_llm = mock_llm_class.return_value
        mock_anon = mock_anon_class.return_value

        yield {
            'server': mock_server,
            'llm': mock_llm,
            'anon': mock_anon,
            'tool_read_file': mock_tool_comp,
            'tool_appointment': mock_appointment_comp
        }


def test_mcp_agent_anonymize_other_role_and_system_prompt(mock_mcp_agent_deps):
    """Tests anonymizing messages that have non-user roles (e.g., assistant) and system prompt anonymization.

    Covers lines: 160, 162, 168.
    """
    agent = MCPAgent(use_cloud=True)
    mock_anon = mock_mcp_agent_deps['anon']
    mock_llm = mock_mcp_agent_deps['llm']

    # Configure mock responses
    mock_anon.anonymize.side_effect = lambda text, name, email: f"ANON_{text}"
    mock_anon.deanonymize_text.side_effect = lambda text: text

    mock_llm.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Hello back'}
    }

    messages = [
        {'role': 'user', 'content': 'Hi professor'},
        {'role': 'assistant', 'content': 'Hello student'} # Line 160: role != 'user'
    ]

    response = agent.chat(
        messages=messages,
        system_prompt="You are a helpful assistant", # Line 161-162, Line 167-168
        sender_name="Max",
        sender_email="max@example.com"
    )

    assert response == "Hello back"

    # Check that system prompt anonymize was called
    mock_anon.anonymize.assert_any_call("You are a helpful assistant", "Max", "max@example.com")


def test_mcp_agent_deanonymize_arguments_and_tool_results(mock_mcp_agent_deps):
    """Tests deanonymizing tool arguments and replacing actual names with placeholders in tool outputs.

    Covers lines: 186-187, 214-215.
    """
    agent = MCPAgent(use_cloud=True)
    mock_anon = mock_mcp_agent_deps['anon']
    mock_llm = mock_mcp_agent_deps['llm']
    mock_tool = mock_mcp_agent_deps['tool_read_file']

    # Configure anonymizer mapping for original name substitution in tool outputs (lines 214-215)
    mock_anon.mapping = {"PLACEHOLDER_NAME": "Original Name"}
    mock_anon.deanonymize_args.side_effect = lambda x: {"path": "decoded.txt"} if "PLACEHOLDER_PATH" in str(x) else x
    mock_anon.deanonymize_text.side_effect = lambda x: x

    # Configure tool output to contain "Original Name", which should be replaced by "PLACEHOLDER_NAME"
    mock_tool.fn.return_value = "This file belongs to Original Name"

    mock_llm.chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {'name': 'read_file', 'arguments': {'path': 'PLACEHOLDER_PATH'}}
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'Finished processing'}
        }
    ]

    agent.chat(
        messages=[{'role': 'user', 'content': 'Read file'}],
        sender_name="Original Name",
        sender_email="original@example.com"
    )

    # Verify tool was called with de-anonymized arguments (decoded.txt instead of PLACEHOLDER_PATH)
    mock_tool.fn.assert_called_once_with(path="decoded.txt")


def test_mcp_agent_appointment_info_last(mock_mcp_agent_deps):
    """Tests that last_appointment_info is populated upon a successful manage_calendar_appointment.

    Covers line: 204.
    """
    agent = MCPAgent()
    mock_llm = mock_mcp_agent_deps['llm']
    mock_tool = mock_mcp_agent_deps['tool_appointment']

    mock_llm.chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {
                        'name': 'manage_calendar_appointment',
                        'arguments': {
                            'start_time': '2023-12-01 10:00',
                            'end_time': '2023-12-01 10:30',
                            'subject': 'Sprechstunde',
                            'student_email': 'student@example.com'
                        }
                    }
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'Termin ist gebucht.'}
        }
    ]

    agent.chat([{'role': 'user', 'content': 'Buche einen Termin.'}])

    # Assert that last_appointment_info is correctly populated with the arguments
    assert agent.last_appointment_info is not None
    assert agent.last_appointment_info['student_email'] == 'student@example.com'


def test_mcp_agent_unavailable_tool(mock_mcp_agent_deps):
    """Tests attempting to invoke a tool that is not available on the server.

    Covers lines: 210-211.
    """
    agent = MCPAgent()
    mock_llm = mock_mcp_agent_deps['llm']

    mock_llm.chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call_1',
                    'function': {
                        'name': 'nonexistent_tool',
                        'arguments': {}
                    }
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'Tool not found.'}
        }
    ]

    response = agent.chat([{'role': 'user', 'content': 'Run missing tool.'}])
    assert response == "Tool not found."


def test_mcp_agent_max_iterations(mock_mcp_agent_deps):
    """Tests that MCPAgent hits and returns the maximum iterations error if it loops 5 times.

    Covers line: 223.
    """
    agent = MCPAgent()
    mock_llm = mock_mcp_agent_deps['llm']

    # Prepare 5 tool responses to force looping past limit
    responses = []
    for i in range(5):
        responses.append({
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': f'call_{i}',
                    'function': {'name': 'read_file', 'arguments': {'path': 'test.txt'}}
                }]
            }
        })

    mock_llm.chat.side_effect = responses

    response = agent.chat([{'role': 'user', 'content': 'Keep reading'}])
    assert response == "Fehler: Maximale Iterationen im MCP Agent erreicht."
