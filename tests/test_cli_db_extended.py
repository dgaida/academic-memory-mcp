"""Tests for CLI DB command and metadata operations."""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from mcp_university.cli.db import db_app, get_store_and_index

runner = CliRunner()


@pytest.fixture
def mock_store_index():
    """Returns a mocked store and index pair."""
    with patch("mcp_university.cli.db.get_store_and_index") as mock_get:
        mock_store = MagicMock()
        mock_idx = MagicMock()
        mock_get.return_value = (mock_store, mock_idx)
        yield mock_store, mock_idx


def test_get_store_and_index():
    """Test get_store_and_index function."""
    with patch("mcp_university.cli.db.get_config") as mock_get_cfg, \
         patch("mcp_university.cli.db.MetadataStore") as mock_store_cls, \
         patch("mcp_university.cli.db.SearchIndex") as mock_idx_cls:

        mock_cfg = MagicMock()
        mock_cfg.sqlite_path = "test.db"
        mock_cfg.qdrant_path = "test_qdrant"
        mock_cfg.embeddings.model = "test-model"
        mock_get_cfg.return_value = mock_cfg

        store, idx = get_store_and_index()
        assert store is mock_store_cls.return_value
        assert idx is mock_idx_cls.return_value
        mock_store_cls.assert_called_with("test.db")


def test_db_list_files_empty(mock_store_index):
    """Test list-files command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_files.return_value = []
    result = runner.invoke(db_app, ["list-files"])
    assert result.exit_code == 0
    assert "Keine Dateien" in result.stdout


def test_db_list_files_non_empty(mock_store_index):
    """Test list-files command when populated."""
    mock_store, _ = mock_store_index
    mock_store.get_all_files.return_value = [
        {'id': 1, 'path': 'test.txt', 'type': 'txt', 'last_indexed': 1234567890}
    ]
    result = runner.invoke(db_app, ["list-files"])
    assert result.exit_code == 0
    assert "test.txt" in result.stdout


def test_db_list_folders_empty(mock_store_index):
    """Test list-folders command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_folders.return_value = []
    result = runner.invoke(db_app, ["list-folders"])
    assert result.exit_code == 0
    assert "Keine Ordner" in result.stdout


def test_db_list_folders_non_empty(mock_store_index):
    """Test list-folders command when populated."""
    mock_store, _ = mock_store_index
    mock_store.get_all_folders.return_value = [
        {'id': 1, 'path': '/path/to/folder', 'last_summarized': 1234567890}
    ]
    result = runner.invoke(db_app, ["list-folders"])
    assert result.exit_code == 0
    assert "/path/to/folder" in result.stdout


def test_db_list_summaries_empty(mock_store_index):
    """Test list-summaries command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = []
    result = runner.invoke(db_app, ["list-summaries"])
    assert result.exit_code == 0
    assert "Keine Zusammenfassungen" in result.stdout


def test_db_list_summaries(mock_store_index):
    """Test db list-summaries command."""
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = [
        {'id': 1, 'item_type': 'folder', 'item_id': 1, 'content': 'Summary content', 'created_at': 1234567890}
    ]
    result = runner.invoke(db_app, ["list-summaries"])
    assert result.exit_code == 0
    assert "Summary content" in result.stdout


def test_db_list_deadlines_empty(mock_store_index):
    """Test list-deadlines command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = []
    result = runner.invoke(db_app, ["list-deadlines"])
    assert result.exit_code == 0
    assert "Keine Deadlines" in result.stdout


def test_db_list_deadlines(mock_store_index):
    """Test db list-deadlines command."""
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = [
        {'id': 1, 'title': 'Deadline 1', 'due_date': 1234567890, 'item_type': 'task'}
    ]
    result = runner.invoke(db_app, ["list-deadlines"])
    assert result.exit_code == 0
    assert "Deadline 1" in result.stdout


def test_db_list_nodes_empty(mock_store_index):
    """Test list-nodes command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_nodes.return_value = []
    result = runner.invoke(db_app, ["list-nodes"])
    assert result.exit_code == 0
    assert "Keine Knoten" in result.stdout


def test_db_list_nodes(mock_store_index):
    """Test db list-nodes command."""
    mock_store, _ = mock_store_index
    mock_store.get_all_nodes.return_value = [
        {'id': 1, 'name': 'Node 1', 'type': 'Person', 'properties_json': '{}'}
    ]
    result = runner.invoke(db_app, ["list-nodes"])
    assert result.exit_code == 0
    assert "Node 1" in result.stdout


def test_db_list_edges_empty(mock_store_index):
    """Test list-edges command when empty."""
    mock_store, _ = mock_store_index
    mock_store.get_all_edges.return_value = []
    result = runner.invoke(db_app, ["list-edges"])
    assert result.exit_code == 0
    assert "Keine Kanten" in result.stdout


def test_db_list_edges_non_empty(mock_store_index):
    """Test list-edges command when populated."""
    mock_store, _ = mock_store_index
    mock_store.get_all_nodes.return_value = [
        {'id': 1, 'name': 'Node 1', 'type': 'Person'}
    ]
    mock_store.get_all_edges.return_value = [
        {'id': 1, 'source_id': 1, 'target_id': 1, 'relation_type': 'FRIEND', 'properties_json': '{}'}
    ]
    result = runner.invoke(db_app, ["list-edges"])
    assert result.exit_code == 0
    assert "FRIEND" in result.stdout


def test_db_delete_file(mock_store_index):
    """Test db delete-file command."""
    mock_store, mock_idx = mock_store_index
    mock_store.get_all_files.return_value = [{'id': 1, 'path': 'test.txt'}]
    
    result = runner.invoke(db_app, ["delete-file", "1", "--force"])
    assert result.exit_code == 0
    mock_idx.delete_document.assert_called_with("test.txt")
    mock_store.delete_file.assert_called_with(1)


def test_db_delete_folder_not_found(mock_store_index):
    """Test delete-folder command when folder not found."""
    mock_store, _ = mock_store_index
    mock_store.get_all_folders.return_value = []
    result = runner.invoke(db_app, ["delete-folder", "99"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout


def test_db_delete_folder_cancel(mock_store_index):
    """Test delete-folder command with cancellation."""
    mock_store, _ = mock_store_index
    mock_store.get_all_folders.return_value = [{'id': 1, 'path': '/folder'}]
    result = runner.invoke(db_app, ["delete-folder", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_folder.assert_not_called()


def test_db_delete_folder_confirm(mock_store_index):
    """Test delete-folder command with confirmation."""
    mock_store, mock_idx = mock_store_index
    mock_store.get_all_folders.return_value = [{'id': 1, 'path': '/folder'}]
    mock_store.get_folder_files.return_value = [(10, 'file1.txt', 'h', 1.0, 'txt', 1, 1)]
    result = runner.invoke(db_app, ["delete-folder", "1", "--force"])
    assert result.exit_code == 0
    mock_idx.delete_document.assert_called_with('file1.txt')
    mock_store.delete_folder.assert_called_with(1)


def test_db_delete_node(mock_store_index):
    """Test db delete-node command."""
    mock_store, _ = mock_store_index
    mock_store.get_node_by_id.return_value = {'id': 1, 'name': 'Node 1', 'type': 'Person'}
    
    result = runner.invoke(db_app, ["delete-node", "1", "--force"])
    assert result.exit_code == 0
    mock_store.delete_node.assert_called_with(1)


def test_db_sync_students_not_found(mock_store_index):
    """Test db sync-students command with missing YAML."""
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(db_app, ["sync-students", "--yaml-path", "missing.yaml"])
        assert result.exit_code == 0
        assert "nicht gefunden" in result.stdout


def test_db_sync_students_invalid_yaml(mock_store_index, tmp_path):
    """Test db sync-students command with invalid or empty YAML."""
    yaml_file = tmp_path / "students.yaml"
    yaml_file.write_text("invalid_content: true")

    result = runner.invoke(db_app, ["sync-students", "--yaml-path", str(yaml_file)])
    assert result.exit_code == 0
    assert "students fehlt" in result.stdout


def test_db_sync_students_success(mock_store_index, tmp_path):
    """Test db sync-students command with valid YAML and logic coverage."""
    yaml_file = tmp_path / "students.yaml"
    yaml_content = """
students:
  - name: "Max Mustermann"
    smail: "max@example.com"
    topic: "My Topic"
    status: "Active"
    folders:
      - path: "/path/to/folder"
  - name: ""
  - email: "no_name@example.com"
"""
    yaml_file.write_text(yaml_content)

    mock_store, _ = mock_store_index
    mock_store.get_all_folders.return_value = [{'id': 10, 'path': '/path/to/folder'}]

    result = runner.invoke(db_app, ["sync-students", "--yaml-path", str(yaml_file)])
    assert result.exit_code == 0
    assert "Studenten synchronisiert" in result.stdout
    mock_store.upsert_student.assert_called_once_with(
        "Max Mustermann", "max@example.com", "My Topic", "Active", 10
    )


def test_db_list_students_empty(mock_store_index):
    """Test db list-students when no students found."""
    mock_store, _ = mock_store_index
    mock_store.get_all_students.return_value = []

    result = runner.invoke(db_app, ["list-students"])
    assert result.exit_code == 0
    assert "Keine Studenten" in result.stdout


def test_db_list_students_non_empty(mock_store_index):
    """Test db list-students when there are students."""
    mock_store, _ = mock_store_index
    mock_store.get_all_students.return_value = [
        {'id': 1, 'name': 'Max Mustermann', 'email': 'max@example.com', 'status': 'Active'}
    ]

    result = runner.invoke(db_app, ["list-students"])
    assert result.exit_code == 0
    assert "Max Mustermann" in result.stdout


def test_db_delete_student_not_found(mock_store_index):
    """Test delete-student when ID doesn't exist."""
    mock_store, _ = mock_store_index
    mock_store.get_all_students.return_value = []

    result = runner.invoke(db_app, ["delete-student", "99"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout


def test_db_delete_student_cancel(mock_store_index):
    """Test delete-student confirmation rejection."""
    mock_store, _ = mock_store_index
    mock_store.get_all_students.return_value = [{'id': 1, 'name': 'Max'}]

    result = runner.invoke(db_app, ["delete-student", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_student.assert_not_called()


def test_db_delete_student_confirm(mock_store_index):
    """Test delete-student confirmation acceptance."""
    mock_store, _ = mock_store_index
    mock_store.get_all_students.return_value = [{'id': 1, 'name': 'Max'}]

    result = runner.invoke(db_app, ["delete-student", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_student.assert_called_with(1)


def test_db_delete_summary_not_found(mock_store_index):
    """Test delete-summary when ID doesn't exist."""
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = []

    result = runner.invoke(db_app, ["delete-summary", "99"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout


def test_db_delete_summary_cancel(mock_store_index):
    """Test delete-summary confirmation rejection."""
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = [{'id': 1}]

    result = runner.invoke(db_app, ["delete-summary", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_summary.assert_not_called()


def test_db_delete_summary_confirm(mock_store_index):
    """Test delete-summary confirmation acceptance."""
    mock_store, _ = mock_store_index
    mock_store.get_all_summaries.return_value = [{'id': 1}]

    result = runner.invoke(db_app, ["delete-summary", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_summary.assert_called_with(1)


def test_db_delete_deadline_not_found(mock_store_index):
    """Test delete-deadline when ID doesn't exist."""
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = []

    result = runner.invoke(db_app, ["delete-deadline", "99"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout


def test_db_delete_deadline_cancel(mock_store_index):
    """Test delete-deadline confirmation rejection."""
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = [{'id': 1, 'title': 'Dl'}]

    result = runner.invoke(db_app, ["delete-deadline", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_deadline.assert_not_called()


def test_db_delete_deadline_confirm(mock_store_index):
    """Test delete-deadline confirmation acceptance."""
    mock_store, _ = mock_store_index
    mock_store.get_all_deadlines.return_value = [{'id': 1, 'title': 'Dl'}]

    result = runner.invoke(db_app, ["delete-deadline", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_deadline.assert_called_with(1)


def test_db_delete_node_not_found(mock_store_index):
    """Test delete-node when ID doesn't exist."""
    mock_store, _ = mock_store_index
    mock_store.get_node_by_id.return_value = None

    result = runner.invoke(db_app, ["delete-node", "99"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout


def test_db_delete_node_cancel(mock_store_index):
    """Test delete-node confirmation rejection."""
    mock_store, _ = mock_store_index
    mock_store.get_node_by_id.return_value = {'id': 1, 'name': 'Node', 'type': 'Person'}

    result = runner.invoke(db_app, ["delete-node", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_node.assert_not_called()


def test_db_delete_edge_cancel(mock_store_index):
    """Test delete-edge confirmation rejection."""
    mock_store, _ = mock_store_index

    result = runner.invoke(db_app, ["delete-edge", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_edge_by_id.assert_not_called()


def test_db_delete_edge_confirm(mock_store_index):
    """Test delete-edge confirmation acceptance."""
    mock_store, _ = mock_store_index

    result = runner.invoke(db_app, ["delete-edge", "1"], input="y\n")
    assert result.exit_code == 0
    mock_store.delete_edge_by_id.assert_called_with(1)


def test_db_delete_file_cancel(mock_store_index):
    """Test delete-file confirmation rejection."""
    mock_store, _ = mock_store_index
    mock_store.get_all_files.return_value = [{'id': 1, 'path': 'test.txt'}]

    result = runner.invoke(db_app, ["delete-file", "1"], input="n\n")
    assert result.exit_code == 0
    mock_store.delete_file.assert_not_called()


def test_db_delete_file_not_found(mock_store_index):
    """Test delete-file when ID doesn't exist."""
    mock_store, _ = mock_store_index
    mock_store.get_all_files.return_value = []

    result = runner.invoke(db_app, ["delete-file", "1"])
    assert result.exit_code == 0
    assert "nicht gefunden" in result.stdout
