"""Tests for test_core.py."""
from mcp_university.config import Config
from mcp_university.metadata.store import MetadataStore
from mcp_university.parser.factory import ParserFactory

def test_config_loading(tmp_path):
    """Test function docstring."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "folders.yaml").write_text("folders: ['/test']")
    (config_dir / "models.yaml").write_text("llm: {model: 'test-model'}\ncalendar: {send_invitations_automatically: true}")

    cfg = Config(config_dir)
    assert cfg.folders.folders == ['/test']
    assert cfg.llm.model == 'test-model'
    assert cfg.calendar.send_invitations_automatically is True

def test_metadata_store(tmp_path):
    """Test function docstring."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path)
    fid = store.upsert_folder("/path/to/folder")
    assert fid is not None

    file_id = store.upsert_file("/path/to/folder/file.txt", "hash1", 100.0, "txt", fid)
    assert file_id is not None

    file = store.get_file("/path/to/folder/file.txt")
    assert file[1] == "/path/to/folder/file.txt"

def test_parser_factory(tmp_path):
    """Test function docstring."""
    cache_dir = tmp_path / "cache"
    factory = ParserFactory(cache_dir)

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    content = factory.parse(test_file)
    assert content == "hello world"
