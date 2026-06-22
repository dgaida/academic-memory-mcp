import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from mcp_university.cli.db import db_app

runner = CliRunner()

@pytest.fixture
def mock_store_index():
    with patch("mcp_university.cli.db.get_store_and_index") as mock_get:
        mock_store = MagicMock()
        mock_idx = MagicMock()
        mock_get.return_value = (mock_store, mock_idx)
        yield mock_store, mock_idx

def test_db_list_summaries(mock_store_index):
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = [
        {'id': 1, 'item_type': 'folder', 'item_id': 1, 'content': 'Summary content', 'created_at': 1234567890}
    ]
    result = runner.invoke(db_app, ["list-summaries"])
    assert result.exit_code == 0
    assert "Summary content" in result.stdout

def test_db_list_deadlines(mock_store_index):
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = [
        {'id': 1, 'title': 'Deadline 1', 'due_date': 1234567890, 'item_type': 'task'}
    ]
    result = runner.invoke(db_app, ["list-deadlines"])
    assert result.exit_code == 0
    assert "Deadline 1" in result.stdout

def test_db_list_nodes(mock_store_index):
    mock_store, _ = mock_store_index
    mock_store.get_all_nodes.return_value = [
        {'id': 1, 'name': 'Node 1', 'type': 'Person', 'properties_json': '{}'}
    ]
    result = runner.invoke(db_app, ["list-nodes"])
    assert result.exit_code == 0
    assert "Node 1" in result.stdout

def test_db_delete_file(mock_store_index):
    mock_store, mock_idx = mock_store_index
    mock_store.get_all_files.return_value = [{'id': 1, 'path': 'test.txt'}]
    
    # Mock confirmation
    result = runner.invoke(db_app, ["delete-file", "1", "--force"])
    assert result.exit_code == 0
    mock_idx.delete_document.assert_called_with("test.txt")
    mock_store.delete_file.assert_called_with(1)

def test_db_delete_node(mock_store_index):
    mock_store, _ = mock_store_index
    mock_store.get_node_by_id.return_value = {'id': 1, 'name': 'Node 1', 'type': 'Person'}
    
    result = runner.invoke(db_app, ["delete-node", "1", "--force"])
    assert result.exit_code == 0
    mock_store.delete_node.assert_called_with(1)
