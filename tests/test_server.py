import pytest
from unittest.mock import MagicMock
import mcp_university.retrieval.index as index_mod
import mcp_university.summarizer.engine as sum_mod

# Mock models to avoid downloads and external calls
index_mod.SentenceTransformer = lambda x: MagicMock()
index_mod.QdrantClient = MagicMock()
sum_mod.ollama = MagicMock()

from mcp_university.mcp_server.server import create_server  # noqa: E402

@pytest.mark.asyncio
async def test_server_tools():
    mcp = create_server()
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "search_documents" in tool_names
    assert "get_folder_summary" in tool_names
    assert "get_student_context" in tool_names
