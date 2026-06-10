import sys
from unittest.mock import MagicMock, patch

# Mock win32com before importing anything that might use it
mock_win32com = MagicMock()
sys.modules["win32com"] = mock_win32com
sys.modules["win32com.client"] = mock_win32com.client

from mcp_university.agent.mcp_agent import MCPAgent  # noqa: E402

def test_mcp_agent_initialization():
    # Mock Ollama Client
    with patch('mcp_university.agent.engine.LLMClientWrapper'):
        agent = MCPAgent(model="test-model", base_url="http://localhost:11434")

        print("Available tools:", list(agent.available_tools.keys()))

        expected_tools = [
            "read_file",
            "search_documents",
            "get_student_info",
            "get_appointment_slots",
            "manage_calendar_appointment"
        ]

        for tool_name in expected_tools:
            if tool_name not in agent.available_tools:
                print(f"FAILED: Tool '{tool_name}' not found in available_tools")
                sys.exit(1)
            else:
                print(f"SUCCESS: Tool '{tool_name}' found.")

        if len(agent.available_tools) < len(expected_tools):
            print(f"FAILED: Expected at least {len(expected_tools)} tools, found {len(agent.available_tools)}")
            sys.exit(1)

        print("MCPAgent initialization functional test PASSED.")

if __name__ == "__main__":
    test_mcp_agent_initialization()
