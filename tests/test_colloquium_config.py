import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch

@pytest.fixture
def temp_dir(tmp_path):
    """Provides a temporary directory."""
    return tmp_path

def test_create_colloquium_config(temp_dir):
    """Tests the creation of the colloquium config JSON."""
    from mcp_university.mcp_server.tool_server import create_tool_server

    with patch("mcp_university.mcp_server.tool_server.MetadataStore"), \
         patch("mcp_university.mcp_server.tool_server.SearchIndex"), \
         patch("mcp_university.mcp_server.tool_server.ParserFactory"), \
         patch("mcp_university.mcp_server.tool_server.get_config"):
        mcp = create_tool_server()

        tools = asyncio.run(mcp.list_tools())
        create_tool = next((t for t in tools if t.name == "create_colloquium_config"), None)
        assert create_tool is not None

        email_folder = temp_dir / "student_name" / "Emails"
        email_folder.mkdir(parents=True)
        email_path = email_folder / "test.msg"
        email_path.write_text("dummy")

        result = create_tool.fn(str(email_path), "Thesis.pdf")
        assert "ERFOLG" in result

        config_path = temp_dir / "student_name" / "config.json"
        assert config_path.exists()
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["pdf"]["filename"] == "Thesis.pdf"

def test_update_colloquium_config(temp_dir):
    """Tests updating the colloquium config JSON."""
    from mcp_university.mcp_server.tool_server import create_tool_server

    mock_store_inst = MagicMock()
    with patch("mcp_university.mcp_server.tool_server.MetadataStore", return_value=mock_store_inst), \
         patch("mcp_university.mcp_server.tool_server.SearchIndex"), \
         patch("mcp_university.mcp_server.tool_server.ParserFactory"), \
         patch("mcp_university.mcp_server.tool_server.get_config"):

        mcp = create_tool_server()

        tools = asyncio.run(mcp.list_tools())
        update_tool = next((t for t in tools if t.name == "update_colloquium_config"), None)
        assert update_tool is not None

        student_dir = temp_dir / "student_name"
        student_dir.mkdir()
        config_path = student_dir / "config.json"
        config_path.write_text(json.dumps({"task":"colloquium", "colloquium": {"date":"", "time":""}}))

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_store_inst._get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (str(student_dir),)

        result = update_tool.fn("student@example.com", "12.05.2026", "14:00")
        assert "ERFOLG" in result

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["colloquium"]["date"] == "12.05.2026"
        assert data["colloquium"]["time"] == "14:00"
