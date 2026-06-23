import pytest
import yaml
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from mcp_university.cli.db import db_app
from mcp_university.cli.main import app as main_app

runner = CliRunner()

@pytest.fixture
def mock_db_deps():
    with patch('mcp_university.cli.db.get_store_and_index') as mock_get:
        mock_store = MagicMock()
        mock_index = MagicMock()
        mock_get.return_value = (mock_store, mock_index)
        yield mock_store, mock_index

def test_cli_list_files_empty(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_all_files.return_value = []
    
    result = runner.invoke(db_app, ["list-files"])
    assert result.exit_code == 0
    assert "Keine Dateien" in result.stdout

def test_cli_list_files_content(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_all_files.return_value = [
        {'id': 1, 'path': 'test.pdf', 'type': 'pdf', 'last_indexed': 1700000000}
    ]
    
    result = runner.invoke(db_app, ["list-files"])
    assert result.exit_code == 0
    assert "test.pdf" in result.stdout

def test_cli_delete_file_success(mock_db_deps):
    mock_store, mock_index = mock_db_deps
    mock_store.get_all_files.return_value = [{'id': 1, 'path': 'test.pdf'}]
    
    result = runner.invoke(db_app, ["delete-file", "1"], input="y\n")
    assert result.exit_code == 0
    assert "gelöscht" in result.stdout
    mock_store.delete_file.assert_called_once_with(1)
    mock_index.delete_document.assert_called_once_with('test.pdf')

def test_profiles_update(tmp_path):
    with patch('mcp_university.cli.main.PersonProfiler') as mock_profiler_cls:
        mock_profiler = mock_profiler_cls.return_value
        result = runner.invoke(main_app, ["profiles", "update", "--email", "test@test.de"])
        assert result.exit_code == 0
        assert "test@test.de" in result.stdout
        mock_profiler.update_profile.assert_called_once_with("test@test.de")

def test_cli_list_folders(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_all_folders.return_value = [
        {'id': 1, 'path': 'students/WS24', 'last_summarized': 1700000000}
    ]
    result = runner.invoke(db_app, ["list-folders"])
    assert result.exit_code == 0
    assert "students/WS24" in result.stdout

def test_cli_delete_folder_success(mock_db_deps):
    mock_store, mock_index = mock_db_deps
    mock_store.get_all_folders.return_value = [{'id': 1, 'path': 'folder1'}]
    mock_store.get_folder_files.return_value = [(101, 'file1.pdf', 'hash', 0, 'pdf', 0, 1)]
    
    result = runner.invoke(db_app, ["delete-folder", "1"], input="y\n")
    assert result.exit_code == 0
    assert "erfolgreich gelöscht" in result.stdout
    mock_index.delete_document.assert_called_once_with('file1.pdf')
    mock_store.delete_folder.assert_called_once_with(1)

def test_cli_list_nodes(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_all_nodes.return_value = [{'id': 1, 'name': "NodeA", 'type': "Person", 'properties_json': "{}"}]
    result = runner.invoke(db_app, ["list-nodes"])
    assert result.exit_code == 0
    assert "NodeA" in result.stdout

def test_cli_delete_node(mock_db_deps):
    mock_store, _ = mock_db_deps
    result = runner.invoke(db_app, ["delete-node", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_node.assert_called_once_with(1)

def test_cli_list_edges(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_all_edges.return_value = [{'id': 1, 'source_id': 1, 'target_id': 2, 'relation_type': 'TEST_REL', 'properties_json': '{}'}]
    mock_store.get_all_nodes.return_value = [{'id': 1, 'name': 'A', 'type': 'T'}, {'id': 2, 'name': 'B', 'type': 'T'}]
    result = runner.invoke(db_app, ["list-edges"])
    assert result.exit_code == 0
    assert "TEST_REL" in result.stdout

def test_cli_delete_edge(mock_db_deps):
    mock_store, _ = mock_db_deps
    result = runner.invoke(db_app, ["delete-edge", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_edge_by_id.assert_called_once_with(1)

def test_cli_delete_node_not_found(mock_db_deps):
    mock_store, _ = mock_db_deps
    mock_store.get_node_by_id.return_value = None
    result = runner.invoke(db_app, ["delete-node", "999"])
    assert "nicht gefunden" in result.stdout
