import pytest
from unittest.mock import MagicMock, patch
from mcp_university.crawler.crawler import Crawler

@pytest.fixture
def mock_deps():
    config = MagicMock()
    config.folders.supported_extensions = [".txt"]
    config.folders.exclude_patterns = []

    store = MagicMock()
    parser = MagicMock()
    summarizer = MagicMock()
    index = MagicMock()

    return config, store, parser, summarizer, index

def test_folder_summarization_skipped_when_unchanged(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.write_text("content")

    # Setup mocks for "already indexed" state
    store.upsert_folder.return_value = 1
    store.get_folder_files.return_value = [(10, str(test_file), "hash", 1.0, ".txt", 1.0, 1)]
    store.get_file.return_value = (10, str(test_file), "hash", 1.0, ".txt", 1.0, 1)
    store.get_summary.side_effect = ["file summary", "folder summary"] # First for file, then for folder

    # Create the summary file on disk to satisfy the existence check
    (tmp_path / ".subdir_summary.md").write_text("folder summary")

    crawler = Crawler(config, store, parser, summarizer, index)

    # Mock _calculate_hash to return the same hash
    with patch.object(Crawler, '_calculate_hash', return_value="hash"):
        summary, changed = crawler._process_directory(subdir)

    assert summary == "folder summary"
    assert changed is False
    assert summarizer.summarize_folder.called is False

def test_folder_summarization_triggered_when_file_deleted(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    remaining_file = subdir / "stay.txt"
    remaining_file.write_text("content")

    # Setup mocks: DB thinks there are two files, one is missing on disk
    store.upsert_folder.return_value = 1
    deleted_file_path = str(subdir / "missing.txt")
    store.get_folder_files.return_value = [
        (10, str(remaining_file), "hash", 1.0, ".txt", 1.0, 1),
        (11, deleted_file_path, "hash", 1.0, ".txt", 1.0, 1)
    ]
    store.get_file.side_effect = [
        (10, str(remaining_file), "hash", 1.0, ".txt", 1.0, 1), # for stay.txt
        (10, str(remaining_file), "hash", 1.0, ".txt", 1.0, 1)  # for stay.txt again in _process_file
    ]
    store.get_summary.side_effect = ["file summary", "old folder summary"]
    summarizer.summarize_folder.return_value = "new folder summary"

    crawler = Crawler(config, store, parser, summarizer, index)

    with patch.object(Crawler, '_calculate_hash', return_value="hash"):
        summary, changed = crawler._process_directory(subdir)

    assert summary == "new folder summary"
    assert changed is True
    assert store.delete_file.called
    assert summarizer.summarize_folder.called

def test_folder_summarization_triggered_when_file_changed(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.write_text("new content")

    # Setup mocks: Hash mismatch
    store.upsert_folder.return_value = 1
    store.get_folder_files.return_value = [(10, str(test_file), "old_hash", 1.0, ".txt", 1.0, 1)]
    store.get_file.return_value = (10, str(test_file), "old_hash", 1.0, ".txt", 1.0, 1)
    store.get_summary.return_value = "old folder summary"

    parser.parse.return_value = "new content"
    summarizer.summarize_file.return_value = "new file summary"
    summarizer.summarize_folder.return_value = "new folder summary"

    crawler = Crawler(config, store, parser, summarizer, index)

    with patch.object(Crawler, '_calculate_hash', return_value="new_hash"):
        summary, changed = crawler._process_directory(subdir)

    assert summary == "new folder summary"
    assert changed is True
    assert summarizer.summarize_folder.called
