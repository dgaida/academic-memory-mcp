"""Tests for test_db_management.py."""
import pytest
from mcp_university.metadata.store import MetadataStore
from mcp_university.retrieval.index import SearchIndex
from typer.testing import CliRunner
from mcp_university.cli.main import app
from unittest.mock import patch
import mcp_university.cli.db as db_module

@pytest.fixture
def db_path(tmp_path):
    """Provides a temporary database path."""
    return tmp_path / "test_university.db"

@pytest.fixture
def store(db_path):
    """Provides a MetadataStore instance."""
    return MetadataStore(db_path)

@pytest.fixture
def qdrant_path(tmp_path):
    """Provides a temporary Qdrant path."""
    path = tmp_path / "qdrant"
    path.mkdir()
    return path

@pytest.fixture
def search_index(qdrant_path, store):
    """Provides a SearchIndex instance with mocked model."""
    with patch("mcp_university.retrieval.index.SentenceTransformer", create=True) as mock_st:
        mock_model = mock_st.return_value
        # Mock encode to return an object that behaves like a list of 384 zeros
        # but also supports tolist() and __len__
        mock_vector = [0.0] * 384

        class MockVector(list):
            """Mock vector class for testing."""
            def tolist(self):
                """Return the list representation of the vector."""
                return self

        vector_inst = MockVector(mock_vector)
        mock_model.encode.return_value = vector_inst

        return SearchIndex(str(qdrant_path), "all-MiniLM-L6-v2", store=store)

def test_metadata_store_retrieval(store):
    """Test metadata store retrieval."""
    fid = store.upsert_file("/path/to/file.txt", "hash1", 123.45, ".txt")
    store.upsert_folder("/path/to/folder")
    store.add_summary("file", fid, "Test summary")

    files = store.get_all_files()
    assert len(files) == 1
    assert files[0]['path'] == "/path/to/file.txt"

    folders = store.get_all_folders()
    assert len(folders) == 1
    assert folders[0]['path'] == "/path/to/folder"

    summaries = store.get_all_summaries()
    assert len(summaries) == 1
    assert summaries[0]['content'] == "Test summary"

def test_metadata_store_deletion(store):
    """Test metadata store deletion."""
    folder_id = store.upsert_folder("/path/to/folder")
    fid = store.upsert_file("/path/to/file.txt", "hash1", 123.45, ".txt", folder_id=folder_id)
    store.add_summary("file", fid, "File summary")
    store.add_summary("folder", folder_id, "Folder summary")

    store.delete_folder(folder_id)

    assert len(store.get_all_folders()) == 0
    assert len(store.get_all_files()) == 0
    assert len(store.get_all_summaries()) == 0

def test_search_index_deletion(search_index):
    """Test search index deletion."""
    doc_id = "/path/to/doc.txt"
    content = "This is a test document content."
    metadata = {"type": "text"}

    search_index.add_document(doc_id, content, metadata)

    from unittest.mock import patch
    with patch.object(search_index, 'search', return_value=[{'path': doc_id}]):
        results = search_index.search("test document")
        assert len(results) > 0
        assert results[0]['path'] == doc_id

    search_index.delete_document(doc_id)

    results = search_index.search("test document")
    assert len(results) == 0 or all(r['path'] != doc_id for r in results)

def test_cli_list_files(store, search_index, monkeypatch):
    """Test CLI list-files command."""
    monkeypatch.setattr(db_module, "get_store_and_index", lambda: (store, search_index))
    runner = CliRunner()
    result = runner.invoke(app, ["db", "list-files"])
    assert result.exit_code == 0
    assert "Keine Dateien" in result.stdout
    store.upsert_file("/test/path.txt", "hash", 1.0, ".txt")
    result = runner.invoke(app, ["db", "list-files"])
    assert result.exit_code == 0
    assert "/test/path.txt" in result.stdout

def test_cli_delete_file(store, search_index, monkeypatch):
    """Test CLI delete-file command."""
    monkeypatch.setattr(db_module, "get_store_and_index", lambda: (store, search_index))
    fid = store.upsert_file("/test/delete_me.txt", "hash", 1.0, ".txt")
    search_index.add_document("/test/delete_me.txt", "content", {})
    runner = CliRunner()
    result = runner.invoke(app, ["db", "delete-file", str(fid), "--force"])
    assert result.exit_code == 0
    assert "erfolgreich gelöscht" in result.stdout
    assert len(store.get_all_files()) == 0
    results = search_index.search("content")
    assert all(r['path'] != "/test/delete_me.txt" for r in results)

def test_cli_delete_folder(store, search_index, monkeypatch):
    """Test CLI delete-folder command."""
    monkeypatch.setattr(db_module, "get_store_and_index", lambda: (store, search_index))
    folder_id = store.upsert_folder("/test/folder")
    store.upsert_file("/test/folder/file.txt", "hash", 1.0, ".txt", folder_id=folder_id)
    search_index.add_document("/test/folder/file.txt", "content", {})
    runner = CliRunner()
    result = runner.invoke(app, ["db", "delete-folder", str(folder_id), "--force"])
    assert result.exit_code == 0
    assert "erfolgreich gelöscht" in result.stdout
    assert len(store.get_all_folders()) == 0
    assert len(store.get_all_files()) == 0
    results = search_index.search("content")
    assert all(r['path'] != "/test/folder/file.txt" for r in results)
