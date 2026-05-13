import pytest
from pathlib import Path
from unittest.mock import MagicMock
from mcp_university.crawler.crawler import Crawler
from mcp_university.config import Config

def test_crawler_file_processing(tmp_path):
    config = Config()
    config.folders.folders = [str(tmp_path)]
    store = MagicMock()
    parser = MagicMock()
    summarizer = MagicMock()
    index = MagicMock()

    # Setup mocks
    parser.parse.return_value = "content"
    summarizer.summarize_file.return_value = "# Summary"
    store.get_file.return_value = None

    crawler = Crawler(config, store, parser, summarizer, index)

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    summary = crawler._process_file(test_file, 1)

    assert summary == "# Summary"
    assert store.upsert_file.called
    assert index.add_document.called
