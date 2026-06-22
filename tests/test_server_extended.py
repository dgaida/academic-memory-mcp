from unittest.mock import patch
from mcp_university.mcp_server.server import create_server

@patch("mcp_university.mcp_server.server.get_config")
@patch("mcp_university.mcp_server.server.MetadataStore")
@patch("mcp_university.mcp_server.server.SearchIndex")
@patch("mcp_university.mcp_server.server.Summarizer")
@patch("mcp_university.mcp_server.server.FastMCP")
def test_create_server(mock_fastmcp, mock_summarizer, mock_index, mock_store, mock_config):
    # Mock config
    cfg = mock_config.return_value
    cfg.sqlite_path = "test.db"
    cfg.qdrant_path = "test_qdrant"
    cfg.embeddings.model = "test-model"
    cfg.llm.model = "test-llm"
    cfg.llm.base_url = "http://test"
    
    mcp_instance = mock_fastmcp.return_value
    
    create_server()
    
    assert mock_fastmcp.called
    # Check if tools were registered
    assert mcp_instance.tool.called

@patch("mcp_university.mcp_server.server.get_config")
@patch("mcp_university.mcp_server.server.MetadataStore")
@patch("mcp_university.mcp_server.server.SearchIndex")
@patch("mcp_university.mcp_server.server.Summarizer")
def test_server_tools(mock_summarizer, mock_index, mock_store, mock_config):
    cfg = mock_config.return_value
    cfg.sqlite_path = "test.db"
    
    # We want to test the tool functions themselves.
    # They are defined inside create_server().
    # We can capture them by mocking mcp.tool.
    
    tools = {}
    def mock_tool(func):
        tools[func.__name__] = func
        return func
    
    with patch("mcp_university.mcp_server.server.FastMCP") as mock_fastmcp:
        mcp_inst = mock_fastmcp.return_value
        mcp_inst.tool.side_effect = mock_tool
        create_server()
        
    # Now 'tools' contains the tool functions
    assert "search_documents" in tools
    assert "get_folder_summary" in tools
    
    # Test search_documents
    mock_index.return_value.search.return_value = [{"score": 0.9}]
    res = tools["search_documents"]("query")
    assert res == [{"score": 0.9}]
    
    # Test get_folder_summary
    mock_conn = mock_store.return_value._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ("Summary text",)
    
    res = tools["get_folder_summary"]("path/to/folder")
    assert res == "Summary text"
