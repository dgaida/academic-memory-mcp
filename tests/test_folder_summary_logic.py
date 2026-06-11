import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.crawler.crawler import Crawler

@pytest.fixture
def mock_components():
    config = MagicMock()
    config.folders.folders = []
    config.folders.supported_extensions = [".txt"]
    config.folders.exclude_patterns = []
    config.user.email = "test@example.com"

    store = MagicMock()
    parser = MagicMock()
    summarizer = MagicMock()
    index = MagicMock()

    # Default mock returns
    store.get_folder_files.return_value = []
    store.get_summary.return_value = None
    store.upsert_folder.return_value = 1
    parser.parse.return_value = "parsed content"
    summarizer.summarize_file.return_value = "file summary"
    summarizer.summarize_folder.return_value = "folder summary content"

    return config, store, parser, summarizer, index

def test_root_folder_summary_location(tmp_path, mock_components):
    config, store, parser, summarizer, index = mock_components
    root_dir = tmp_path / "my_root"
    root_dir.mkdir()
    (root_dir / "file.txt").write_text("content")

    crawler = Crawler(config, store, parser, summarizer, index)

    # Process as root (parent_id=None)
    crawler._process_directory(root_dir, parent_id=None)

    # Should be inside root as .summary.md
    summary_path = root_dir / ".summary.md"
    assert summary_path.exists()
    assert summary_path.read_text() == "folder summary content"

    # Check that relative path "my_root" was passed to summarizer
    summarizer.summarize_folder.assert_called_with("my_root", ["file summary"])

def test_subfolder_summary_location(tmp_path, mock_components):
    config, store, parser, summarizer, index = mock_components
    root_dir = tmp_path / "my_root"
    sub_dir = root_dir / "my_sub"
    sub_dir.mkdir(parents=True)
    (sub_dir / "file.txt").write_text("content")

    crawler = Crawler(config, store, parser, summarizer, index)

    # Process as subfolder (parent_id=123)
    # We also need to mock relative_path to simulate a real crawl
    crawler._process_directory(sub_dir, parent_id=123, relative_path=Path("my_root/my_sub"))

    # Should be in parent as .my_sub_summary.md
    summary_path = root_dir / ".my_sub_summary.md"
    assert summary_path.exists()
    assert summary_path.read_text() == "folder summary content"

    # Check that relative path was passed
    summarizer.summarize_folder.assert_called_with("my_root/my_sub", ["file summary"])

def test_recursive_path_building(tmp_path, mock_components):
    config, store, parser, summarizer, index = mock_components
    root_dir = tmp_path / "A"
    sub_dir = root_dir / "B"
    sub_dir.mkdir(parents=True)
    (sub_dir / "f.txt").write_text("c")

    crawler = Crawler(config, store, parser, summarizer, index)

    # Start crawl at root
    crawler._process_directory(root_dir)

    # For folder B, relative path should be "A/B"
    calls = summarizer.summarize_folder.call_args_list

    paths_passed = [c.args[0] for c in calls]
    assert "A/B" in paths_passed
    assert "A" in paths_passed

def test_summary_recreation_on_missing_file(tmp_path, mock_components):
    config, store, parser, summarizer, index = mock_components
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    (root_dir / "f.txt").write_text("c")

    # Mock database to say summary IS there
    store.get_summary.return_value = "old summary"

    crawler = Crawler(config, store, parser, summarizer, index)

    # 1. Run - summary exists in DB but NOT on disk
    summary_path = root_dir / ".summary.md"
    assert not summary_path.exists()

    crawler._process_directory(root_dir)

    # Should have been recreated
    assert summary_path.exists()
    summarizer.summarize_folder.assert_called()
