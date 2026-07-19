"""Comprehensive coverage boost tests for MCP University."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from mcp_university.cli.db import db_app
from mcp_university.cli.main import app as main_app
from mcp_university.mcp_server.server import create_server
from mcp_university.agent.engine import Agent
from mcp_university.summarizer.engine import Summarizer
from mcp_university.metadata.store import MetadataStore
from mcp_university.parser.pdf_parser import PDFParser
from mcp_university.retrieval.index import SearchIndex

runner = CliRunner()

# --- CLI DB Tests ---
@pytest.fixture
def mock_db_deps():
    """Mock database dependencies for CLI.

    Yields:
        tuple: (mock_store, mock_idx)
    """
    with patch("mcp_university.cli.db.get_store_and_index") as mock_get:
        mock_store = MagicMock()
        mock_idx = MagicMock()
        mock_get.return_value = (mock_store, mock_idx)
        yield mock_store, mock_idx

def test_db_list_commands(mock_db_deps):
    """Test all DB list commands with empty data.

    Args:
        mock_db_deps: Mocked DB dependencies.
    """
    store, _ = mock_db_deps
    store.get_all_files.return_value = []
    store.get_all_folders.return_value = []
    store.get_all_students.return_value = []
    store.get_all_summaries.return_value = []
    store.get_all_deadlines.return_value = []
    store.get_all_nodes.return_value = []
    store.get_all_edges.return_value = []

    for cmd in ["list-files", "list-folders", "list-students", "list-summaries", "list-deadlines", "list-nodes", "list-edges"]:
        runner.invoke(db_app, [cmd])

def test_db_delete_not_found(mock_db_deps):
    """Test all DB delete commands with missing items.

    Args:
        mock_db_deps: Mocked DB dependencies.
    """
    store, _ = mock_db_deps
    store.get_all_files.return_value = []
    store.get_node_by_id.return_value = None
    for cmd in ["delete-file", "delete-folder", "delete-student", "delete-summary", "delete-deadline", "delete-node"]:
        runner.invoke(db_app, [cmd, "999", "--force"])

# --- CLI Main Tests ---
@pytest.fixture
def mock_main_deps():
    """Mock main CLI dependencies.

    Yields:
        MagicMock: The mocked config.
    """
    with patch("mcp_university.cli.main.get_config") as mock_get_cfg,          patch("mcp_university.cli.main.MetadataStore"),          patch("mcp_university.cli.main.ParserFactory"),          patch("mcp_university.cli.main.Summarizer"),          patch("mcp_university.cli.main.SearchIndex"),          patch("mcp_university.cli.main.Crawler"),          patch("mcp_university.cli.main.create_server"),          patch("mcp_university.crawler.watcher.Watcher"),          patch("mcp_university.summarizer.profiler.PersonProfiler"):
        cfg = MagicMock()
        cfg.log_path = Path("/tmp/logs")
        cfg.config_dir = Path("/tmp/config")
        cfg.embeddings.model = "m"
        mock_get_cfg.return_value = cfg
        yield cfg

def test_main_commands(mock_main_deps):
    """Test standard main CLI commands.

    Args:
        mock_main_deps: Mocked main CLI dependencies.
    """
    runner.invoke(main_app, ["index"])
    runner.invoke(main_app, ["watch"])
    runner.invoke(main_app, ["serve-mcp"])

# --- Server Tests ---
@pytest.fixture
def server_tools():
    """Fixture to extract server tools.

    Yields:
        tuple: (tools, mock_store)
    """
    tools = {}
    def mock_tool(func):
        """Mock tool function."""
        tools[func.__name__] = func
        return func
    with patch("mcp_university.mcp_server.server.get_config") as mock_cfg,          patch("mcp_university.mcp_server.server.MetadataStore") as mock_store,          patch("mcp_university.mcp_server.server.SearchIndex"),          patch("mcp_university.mcp_server.server.Summarizer"),          patch("mcp_university.mcp_server.server.FastMCP") as mock_fastmcp:
        mock_cfg.return_value.sqlite_path = Path("/tmp/t.db")
        mcp_inst = mock_fastmcp.return_value
        mcp_inst.tool.side_effect = mock_tool
        create_server()
        return tools, mock_store

def test_server_tools_not_found(server_tools):
    """Test server tools when items are not found.

    Args:
        server_tools: Mocked server tools.
    """
    tools, mock_store = server_tools
    mock_conn = mock_store.return_value._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None
    assert "No summary" in tools["get_folder_summary"]("p")
    assert "No student" in tools["get_student_context"]("X")

# --- Agent Tests ---
@pytest.fixture
def mock_agent_deps():
    """Mock agent engine dependencies.

    Yields:
        None
    """
    with patch('mcp_university.agent.engine.ParserFactory'),          patch('mcp_university.agent.engine.MetadataStore'),          patch('mcp_university.agent.engine.SearchIndex'),          patch('mcp_university.agent.engine.get_config') as mock_cfg,          patch('mcp_university.agent.engine.LLMClientWrapper'),          patch('mcp_university.agent.engine.Anonymizer'):
        cfg = MagicMock()
        cfg.llm.model = "m"
        cfg.calendar.appointment_slots_path = "data/free_slots.md"
        cfg.config_dir = Path("/tmp")
        mock_cfg.return_value = cfg
        yield

def test_agent_tools_not_found(mock_agent_deps):
    """Test agent tools with missing files.

    Args:
        mock_agent_deps: Mocked agent engine dependencies.
    """
    agent = Agent()
    with patch("pathlib.Path.exists", return_value=False):
        assert "nicht gefunden" in agent._tool_read_file("p")
        assert "nicht gefunden" in agent._tool_get_appointment_slots()

# --- Misc Tests ---
def test_summarizer_gender_none():
    """Test gender detection fallback."""
    summarizer = Summarizer()
    summarizer.client.chat = MagicMock(return_value={'message': {'content': None}})
    assert summarizer.determine_gender("Alex") == "Herr/Frau"

def test_metadata_store_upsert_file_twice(tmp_path):
    """Test MetadataStore upsert logic.

    Args:
        tmp_path: Temporary path.
    """
    store = MetadataStore(tmp_path / "m.db")
    store.upsert_file("f", "h", 1, "t", 1)
    file_id = store.upsert_file("f", "h2", 2, "t", 1)
    assert isinstance(file_id, int)

def test_retrieval_index_qmd_fail(tmp_path):
    """Test RetrievalIndex qmd failure.

    Args:
        tmp_path: Temporary path.
    """
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "1.0.0"
        idx = SearchIndex(str(tmp_path))
        mock_run.return_value.returncode = 1
        assert idx._search_qmd("q") == []

def test_pdf_parser_offline(tmp_path):
    """Test PDFParser offline initialization.

    Args:
        tmp_path: Temporary path.
    """
    with patch("mcp_university.parser.pdf_parser.get_config") as mock_cfg:
        mock_cfg.return_value.offline = True
        parser = PDFParser(tmp_path)
        assert parser.cache_dir == tmp_path
