"""Tests for colloquium flow."""
import json
import pytest
from unittest.mock import MagicMock, patch
import sys
import asyncio

# Ensure mocks are in place for the test environment
sys.modules["win32com"] = MagicMock()
sys.modules["win32com.client"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
sys.modules["numpy"] = MagicMock()

@pytest.fixture
def temp_dir(tmp_path):
    """Provides a temporary directory."""
    return tmp_path

def test_create_colloquium_config_no_overwrite(temp_dir):
    """Tests that create_colloquium_config does not overwrite existing config but updates filename."""
    from mcp_university.mcp_server.tool_server import create_tool_server

    with patch("mcp_university.mcp_server.tool_server.MetadataStore"),          patch("mcp_university.mcp_server.tool_server.SearchIndex"),          patch("mcp_university.mcp_server.tool_server.ParserFactory"),          patch("mcp_university.mcp_server.tool_server.get_config"):
        mcp = create_tool_server()
        
        tools = asyncio.run(mcp.list_tools())
        create_tool = next((t for t in tools if t.name == "create_colloquium_config"), None)
        assert create_tool is not None
        create_tool_fn = create_tool.fn

        student_dir = temp_dir / "student_name"
        email_folder = student_dir / "Emails"
        email_folder.mkdir(parents=True)
        email_path = email_folder / "test.msg"
        email_path.write_text("dummy")

        config_path = student_dir / "config.json"
        initial_data = {
            "task": "colloquium",
            "pdf": {"filename": "Old.pdf"},
            "colloquium": {"date": "01.01.2025", "time": "10:00"}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        result = create_tool_fn(str(email_path), "New_Thesis.pdf")
        assert "ERFOLG" in result

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["pdf"]["filename"] == "New_Thesis.pdf"
        assert data["colloquium"]["date"] == "01.01.2025"

def test_update_colloquium_config_create_if_missing(temp_dir):
    """Tests that update_colloquium_config creates config if it doesn't exist."""
    from mcp_university.mcp_server.tool_server import create_tool_server

    mock_store_inst = MagicMock()
    with patch("mcp_university.mcp_server.tool_server.MetadataStore", return_value=mock_store_inst),          patch("mcp_university.mcp_server.tool_server.SearchIndex"),          patch("mcp_university.mcp_server.tool_server.ParserFactory"),          patch("mcp_university.mcp_server.tool_server.get_config"):

        mcp = create_tool_server()
        tools = asyncio.run(mcp.list_tools())
        update_tool = next((t for t in tools if t.name == "update_colloquium_config"), None)
        assert update_tool is not None
        update_tool_fn = update_tool.fn

        student_dir = temp_dir / "student_name"
        student_dir.mkdir()
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_store_inst._get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (str(student_dir),)

        result = update_tool_fn("student@example.com", "12.05.2026", "14:00")
        assert "ERFOLG" in result

        config_path = student_dir / "config.json"
        assert config_path.exists()
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["colloquium"]["date"] == "12.05.2026"
        assert data["colloquium"]["time"] == "14:00"
        assert data["pdf"]["filename"] == ""

def test_tool_signatures():
    """Verify that the tools have the expected parameters."""
    from mcp_university.mcp_server.tool_server import create_tool_server
    
    with patch("mcp_university.mcp_server.tool_server.MetadataStore"),          patch("mcp_university.mcp_server.tool_server.SearchIndex"),          patch("mcp_university.mcp_server.tool_server.ParserFactory"),          patch("mcp_university.mcp_server.tool_server.get_config"):
        mcp = create_tool_server()
        tools = asyncio.run(mcp.list_tools())
        
        manage_tool = next(t for t in tools if t.name == "manage_calendar_appointment")
        # Check if is_colloquium is in the parameters schema
        props = manage_tool.parameters["properties"]
        assert "is_colloquium" in props
