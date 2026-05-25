import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent import Agent


@pytest.fixture
def mock_ollama_client():
    with patch("ollama.Client") as mock:
        yield mock


@pytest.fixture
def agent(mock_ollama_client):
    # Mocking dependencies that Agent initializes
    with (
        patch("mcp_university.agent.engine.ParserFactory"),
        patch("mcp_university.agent.engine.MetadataStore"),
        patch("mcp_university.agent.engine.SearchIndex"),
    ):
        return Agent(model="test-model", base_url="http://test-url")


def test_agent_initialization(agent):
    assert agent.model == "test-model"
    assert agent.base_url == "http://test-url"
    assert "read_file" in agent.available_tools
    assert "search_documents" in agent.available_tools
    assert "get_appointment_slots" in agent.available_tools
    assert "manage_calendar_appointment" in agent.available_tools


def test_agent_chat_no_tools(agent, mock_ollama_client):
    # Mock Ollama response with no tool calls
    mock_response = {
        "message": {"role": "assistant", "content": "Hello! How can I help you?"}
    }
    agent.client.chat.return_value = mock_response

    response = agent.chat([{"role": "user", "content": "Hi"}])

    assert response == "Hello! How can I help you?"
    agent.client.chat.assert_called_once()


def test_agent_chat_with_tool_call(agent, mock_ollama_client):
    # First response triggers a tool call
    mock_response_1 = {
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "test.txt"},
                    },
                }
            ],
        }
    }
    # Second response (after tool execution) provides the final answer
    mock_response_2 = {
        "message": {
            "role": "assistant",
            "content": "The content of the file is: Hello World",
        }
    }

    agent.client.chat.side_effect = [mock_response_1, mock_response_2]

    # Mock the tool execution and update available_tools
    agent._tool_read_file = MagicMock(return_value="Hello World")
    agent.available_tools["read_file"] = agent._tool_read_file

    response = agent.chat([{"role": "user", "content": "Read test.txt"}])

    assert response == "The content of the file is: Hello World"
    agent._tool_read_file.assert_called_with(path="test.txt")
    assert agent.client.chat.call_count == 2


def test_tool_read_file(agent):
    with patch.object(agent.parser_factory, "parse", return_value="File content"):
        with patch("pathlib.Path.exists", return_value=True):
            result = agent._tool_read_file("some_path.txt")
            assert result == "File content"


def test_tool_read_file_not_found(agent):
    with patch("pathlib.Path.exists", return_value=False):
        result = agent._tool_read_file("non_existent.txt")
        assert "nicht gefunden" in result


def test_tool_get_appointment_slots(agent):
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value="Slots content"):
            result = agent._tool_get_appointment_slots()
            assert result == "Slots content"


def test_tool_get_appointment_slots_not_found(agent):
    with patch("pathlib.Path.exists", return_value=False):
        result = agent._tool_get_appointment_slots()
        assert "nicht gefunden" in result


def test_tool_manage_calendar_appointment_import_error(agent):
    with patch.dict("sys.modules", {"win32com": None, "win32com.client": None}):
        result = agent._tool_manage_calendar_appointment(
            "2026-06-01 13:30", "2026-06-01 14:00", "Subject", "student@example.com"
        )
        assert "pywin32 ist nicht installiert" in result


@patch("mcp_university.agent.engine.Agent._tool_manage_calendar_appointment")
def test_agent_chat_with_appointment_booked(mock_tool, agent, mock_ollama_client):
    # Mock the tool to return success
    mock_tool.return_value = "ERFOLG: Termin eingetragen"

    # Mock Ollama to call the tool and then return the signal word
    mock_response_1 = {
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "manage_calendar_appointment",
                        "arguments": {
                            "start_time": "2026-06-01 13:30",
                            "end_time": "2026-06-01 14:00",
                            "subject": "Test",
                            "student_email": "student@example.com",
                        },
                    },
                }
            ],
        }
    }
    mock_response_2 = {
        "message": {"role": "assistant", "content": "APPOINTMENT_BOOKED"}
    }

    agent.client.chat.side_effect = [mock_response_1, mock_response_2]

    response = agent.chat([{"role": "user", "content": "Bestätige Termin"}])

    assert response == "APPOINTMENT_BOOKED"
    assert agent.client.chat.call_count == 2
