"""Tests for test_cli_commands.py."""
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch, mock_open
from mcp_university.cli.main import app
from mcp_university.cli.db import db_app
from pathlib import Path

runner = CliRunner()

def test_cli_main_help():
    """Tests test_cli_main_help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout

@patch("mcp_university.cli.main.PersonProfiler")
@patch("mcp_university.cli.main.setup_logging")
def test_profiles_update(mock_setup, mock_profiler):
    """Tests test_profiles_update."""
    result = runner.invoke(app, ["profiles", "update", "--email", "test@example.com"])
    assert result.exit_code == 0
    mock_profiler.return_value.update_profile.assert_called_with("test@example.com")

@patch("mcp_university.cli.main.PersonProfiler")
@patch("mcp_university.cli.main.setup_logging")
def test_profiles_update_all(mock_setup, mock_profiler):
    """Tests test_profiles_update_all."""
    result = runner.invoke(app, ["profiles", "update"])
    assert result.exit_code == 0
    mock_profiler.return_value.update_all_profiles.assert_called_once()

@patch("mcp_university.cli.main.MetadataStore")
@patch("mcp_university.cli.main.Summarizer")
@patch("mcp_university.cli.main.KnowledgeGraphEngine")
@patch("mcp_university.cli.main.get_config")
@patch("mcp_university.cli.main.setup_logging")
@patch("mcp_university.cli.main.yaml.safe_load")
@patch("builtins.open", new_callable=mock_open, read_data="class_paths: {}")
def test_graph_build(mock_open, mock_load, mock_setup, mock_config, mock_kg, mock_summarizer, mock_store):
    """Tests test_graph_build."""
    cfg = MagicMock()
    cfg.config_dir = Path("config")
    cfg.user.name = "User"
    cfg.user.email = "user@example.com"
    mock_config.return_value = cfg
    mock_load.return_value = {"class_paths": {}}
    mock_store.return_value.upsert_node.return_value = (1, True)
    
    result = runner.invoke(app, ["graph", "build"])
    assert result.exit_code == 0

@patch("mcp_university.cli.db.get_store_and_index")
def test_db_list_files(mock_get_store):
    """Tests test_db_list_files."""
    mock_store = MagicMock()
    mock_store.get_all_files.return_value = [
        {'id': 1, 'path': 'test.txt', 'type': 'text', 'last_indexed': 1234567890}
    ]
    mock_get_store.return_value = (mock_store, MagicMock())
    
    result = runner.invoke(db_app, ["list-files"])
    assert result.exit_code == 0
    assert "test.txt" in result.stdout

@patch("mcp_university.cli.main.SearchIndex")
@patch("mcp_university.cli.main.MetadataStore")
@patch("mcp_university.cli.main.Summarizer")
@patch("mcp_university.cli.main.get_config")
@patch("mcp_university.cli.main.setup_logging")
def test_main_search(mock_setup, mock_config, mock_summarizer, mock_store, mock_idx):
    """Tests test_main_search."""
    mock_idx.return_value.search.return_value = [
        {'score': 0.9, 'filename': 'test.txt', 'path': 'path/test.txt', 'content': 'content'}
    ]
    result = runner.invoke(app, ["search", "query"])
    assert result.exit_code == 0
    assert "test.txt" in result.stdout

@patch("mcp_university.cli.memory.Path.exists")
def test_memory_update_error(mock_exists):
    """Tests test_memory_update_error."""
    mock_exists.return_value = False
    with patch("mcp_university.cli.main.setup_logging"):
        # The memory_app itself is a Typer object, so we call its commands.
        # But wait, memory_app is added to 'app' as 'memory'.
        # runner.invoke(memory_app, ["update"]) should work IF we don't pass the name "update"
        # as if it was a subcommand of memory_app if memory_app ONLY has that command?
        # No, memory_app has .command("update"), so we DO need "update".
        # The error "Got unexpected extra argument (update)" suggests memory_app 
        # is being invoked such that it doesn't think it has subcommands.
        # Let's try invoking from the root 'app'.
        result = runner.invoke(app, ["memory", "update", "-c", "missing.yaml"])
    assert result.exit_code == 0

@patch("mcp_university.cli.memory.process_memory_folder")
@patch("mcp_university.cli.memory.SearchIndex")
@patch("mcp_university.cli.memory.ParserFactory")
@patch("mcp_university.cli.memory.AutoTokenizer")
@patch("mcp_university.cli.memory.get_config")
@patch("mcp_university.cli.memory.resolve_memory_index_names")
@patch("mcp_university.cli.memory.yaml.safe_load")
@patch("mcp_university.cli.memory.open", new_callable=mock_open, read_data="class_paths: {class1: /path1}")
@patch("mcp_university.cli.memory.Path.exists")
@patch("mcp_university.cli.memory.Path.mkdir")
def test_memory_update_success(mock_mkdir, mock_exists, mock_open, mock_load, mock_resolve, mock_config, mock_tokenizer, mock_pf, mock_idx, mock_process):
    """Tests test_memory_update_success."""
    mock_exists.return_value = True
    mock_load.return_value = {"class_paths": {"class1": "/path1"}}
    mock_resolve.return_value = {"class1": "index1"}
    
    with patch("mcp_university.cli.main.setup_logging"):
        result = runner.invoke(app, ["memory", "update"])
    
    assert result.exit_code == 0
