"""Tests for mcp_server/server.py."""
import subprocess
import runpy
from unittest.mock import MagicMock, patch, ANY
import pytest
from pathlib import Path
from mcp_university.mcp_server.server import create_server


@patch("mcp_university.mcp_server.server.get_config")
@patch("mcp_university.mcp_server.server.MetadataStore")
@patch("mcp_university.mcp_server.server.SearchIndex")
@patch("mcp_university.mcp_server.server.Summarizer")
@patch("mcp_university.mcp_server.server.FastMCP")
def test_create_server(
    mock_fastmcp: MagicMock,
    mock_summarizer: MagicMock,
    mock_index: MagicMock,
    mock_store: MagicMock,
    mock_config: MagicMock,
) -> None:
    """Tests the create_server initialization.

    Args:
        mock_fastmcp: Mock for FastMCP.
        mock_summarizer: Mock for Summarizer.
        mock_index: Mock for SearchIndex.
        mock_store: Mock for MetadataStore.
        mock_config: Mock for get_config.

    Returns:
        None
    """
    cfg = mock_config.return_value
    cfg.sqlite_path = "test.db"
    cfg.qdrant_path = "test_qdrant"
    cfg.embeddings.model = "test-model"
    cfg.llm.model = "test-llm"
    cfg.llm.base_url = "http://test"

    mcp_instance = mock_fastmcp.return_value

    create_server()

    assert mock_fastmcp.called
    assert mcp_instance.tool.called


@patch("mcp_university.mcp_server.server.get_config")
@patch("mcp_university.mcp_server.server.MetadataStore")
@patch("mcp_university.mcp_server.server.SearchIndex")
@patch("mcp_university.mcp_server.server.Summarizer")
def test_server_tools(
    mock_summarizer: MagicMock,
    mock_index: MagicMock,
    mock_store: MagicMock,
    mock_config: MagicMock,
) -> None:
    """Tests all tool registrations and their invocation.

    Args:
        mock_summarizer: Mock for Summarizer.
        mock_index: Mock for SearchIndex.
        mock_store: Mock for MetadataStore.
        mock_config: Mock for get_config.

    Returns:
        None
    """
    cfg = mock_config.return_value
    cfg.sqlite_path = "test.db"
    cfg.data_dir = Path("/tmp/data")

    tools = {}

    def mock_tool(func):
        tools[func.__name__] = func
        return func

    with patch("mcp_university.mcp_server.server.FastMCP") as mock_fastmcp:
        mcp_inst = mock_fastmcp.return_value
        mcp_inst.tool.side_effect = mock_tool
        create_server()

    assert "search_documents" in tools
    assert "get_folder_summary" in tools
    assert "get_student_context" in tools
    assert "generate_mail_reply" in tools
    assert "get_open_tasks" in tools
    assert "compare_document_versions" in tools
    assert "run_qmd_command" in tools

    # 1. Test search_documents
    mock_index_instance = mock_index.return_value
    mock_index_instance.search.return_value = [{"score": 0.9}]
    res = tools["search_documents"]("query", top_k=3)
    assert res == [{"score": 0.9}]
    mock_index_instance.search.assert_called_with("query", top_k=3)

    # 2. Test get_folder_summary (found and not found)
    mock_conn = mock_store.return_value._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value

    # Case A: Found summary
    mock_cursor.fetchone.return_value = ("Summary text",)
    res = tools["get_folder_summary"]("path/to/folder")
    assert res == "Summary text"

    # Case B: Not found summary
    mock_cursor.fetchone.return_value = None
    res = tools["get_folder_summary"]("path/to/missing")
    assert res == "No summary found for folder path/to/missing"

    # 3. Test get_student_context
    # Case A: Student not found
    mock_cursor.fetchone.return_value = None
    res = tools["get_student_context"]("John Doe")
    assert res == "No student found with name John Doe"

    # Case B: Student found, folder_path is None
    # student structure: (id, name, email, topic, status, folder_id, folder_path)
    mock_cursor.fetchone.return_value = (1, "John Doe", "john@example.com", "Thesis", "Active", 10, None)
    res = tools["get_student_context"]("John Doe")
    assert "Student: John Doe" in res
    assert "Email: john@example.com" in res
    assert "Folder Summary:" not in res

    # Case C: Student found, folder_path is set, summary found
    # We will mock fetchone to return the student info, then for the subsequent folder summary query, we mock fetchone to return summary.
    mock_cursor.fetchone.side_effect = [
        (1, "John Doe", "john@example.com", "Thesis", "Active", 10, "path/to/folder"),
        ("Folder summary text here",)
    ]
    res = tools["get_student_context"]("John")
    assert "Student: John Doe" in res
    assert "Folder Summary:" in res
    assert "Folder summary text here" in res

    # 4. Test generate_mail_reply
    # Ensure summarizer returns draft
    mock_cursor.fetchone.side_effect = [
        (1, "Jane", "jane@example.com", "Topic", "Active", 11, None),
    ]
    mock_summarizer_instance = mock_summarizer.return_value
    mock_summarizer_instance.summarize_file.return_value = "Draft response text."
    res = tools["generate_mail_reply"]("Jane", "Hello Prof")
    assert res == "Draft response text."
    mock_summarizer_instance.summarize_file.assert_called_with("reply_draft", ANY)

    # 5. Test get_open_tasks
    # Case A: No tasks found
    mock_index_instance.search.return_value = []
    res = tools["get_open_tasks"]()
    assert res == "No open tasks found."

    # Case B: Tasks found (some with filename, some without)
    mock_index_instance.search.return_value = [
        {"content": "First task to do", "filename": "todo.txt"},
        {"content": "Second task to do"},
    ]
    res = tools["get_open_tasks"]()
    assert "- From todo.txt: First task to do" in res
    assert "- From Unknown: Second task to do" in res

    # 6. Test compare_document_versions
    # Mock ParserFactory
    with patch("academic_parser.factory.ParserFactory") as mock_factory_cls:
        mock_factory = mock_factory_cls.return_value

        # Case A: One of the files could not be read
        mock_factory.parse.side_effect = ["", "Some parsed content"]
        res = tools["compare_document_versions"]("file1.pdf", "file2.pdf")
        assert res == "Could not read one of the files for comparison."

        # Case B: Both successfully read
        mock_factory.parse.side_effect = ["Version 1 parsed content", "Version 2 parsed content"]
        mock_summarizer_instance.summarize_file.return_value = "Comparison summary output."
        res = tools["compare_document_versions"]("v1.pdf", "v2.pdf")
        assert res == "Comparison summary output."
        mock_summarizer_instance.summarize_file.assert_called_with("comparison", ANY)

    # 7. Test run_qmd_command
    with patch("subprocess.run") as mock_run:
        # Case A: Successful execution (returncode = 0)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "qmd command stdout"
        mock_run.return_value = mock_proc

        res = tools["run_qmd_command"]("ls", ["arg1"])
        assert res == "qmd command stdout"
        mock_run.assert_called_with(["qmd", "ls", "arg1"], capture_output=True, text=True, shell=ANY)

        # Case B: Unsuccessful execution (returncode != 0)
        mock_proc.returncode = 1
        mock_proc.stderr = "error output"
        res = tools["run_qmd_command"]("ls", ["arg1"])
        assert res == "Error: error output"

        # Case C: Exception raised
        mock_run.side_effect = OSError("qmd not found")
        res = tools["run_qmd_command"]("ls", ["arg1"])
        assert res == "Exception: qmd not found"


@patch("fastmcp.FastMCP.run")
def test_server_main_execution(mock_run: MagicMock) -> None:
    """Tests execution of the server module when run as __main__.

    Args:
        mock_run: Mock for FastMCP run method.

    Returns:
        None
    """
    # Use runpy to run the server.py as __main__
    runpy.run_module("mcp_university.mcp_server.server", run_name="__main__")

    assert mock_run.called
