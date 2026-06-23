"""Tests for test_server.py."""
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_server_tools(mock_llm_client_wrapper):
    # Mock models to avoid downloads and external calls
    with patch("mcp_university.retrieval.index.SentenceTransformer"),          patch("mcp_university.retrieval.index.QdrantClient"):

        from mcp_university.mcp_server.server import create_server
        mcp = create_server()
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        assert "search_documents" in tool_names
        assert "get_folder_summary" in tool_names
        assert "get_student_context" in tool_names
