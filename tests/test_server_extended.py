"""Tests for test_server_extended.py."""
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_server_tools_extended(mock_llm_client_wrapper):
    """Test function docstring.

    Args:
        mock_llm_client_wrapper: Mock for the LLM client.
    """
    # Mock models to avoid downloads and external calls
    with patch("mcp_university.retrieval.index.SentenceTransformer"),          patch("mcp_university.retrieval.index.QdrantClient"):

        from mcp_university.mcp_server.server import create_server
        mcp = create_server()
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        assert "search_documents" in tool_names
