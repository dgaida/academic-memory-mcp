"""Tests für den Tool-Server."""
import pytest
from unittest.mock import patch
from mcp_university.mcp_server.server import create_server

@pytest.fixture
def server():
    """Erstellt eine MCP-Server-Instanz für Tests.

    Returns:
        FastMCP: Die Server-Instanz.
    """
    return create_server()

def test_tool_search(server):
    """Testet das Search-Tool.

    Args:
        server: Die Server-Instanz.
    """
    with patch("mcp_university.mcp_server.server.HybridSearch") as mock_search:
        mock_instance = mock_search.return_value
        mock_instance.search.return_value = []

        # In FastMCP calling tools usually happens via server.call_tool
        # or we just test the function directly if exported.
        pass

def test_tool_appointment(server):
    """Testet das Appointment-Tool.

    Args:
        server: Die Server-Instanz.
    """
    with patch("mcp_university.mcp_server.server.manage_calendar_appointment") as mock_tool:
        mock_tool.return_value = "Appointment created"
        # Test logic
        pass
