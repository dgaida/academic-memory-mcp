"""Tests for test_watcher.py."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.crawler.watcher import IndexingHandler, Watcher

@pytest.fixture
def mock_crawler():
    """Test function docstring."""
    crawler = MagicMock()
    crawler.config.folders.supported_extensions = [".pdf", ".md", ".msg"]
    crawler.config.folders.folders = ["/tmp/watch"]
    return crawler

def test_indexing_handler_on_modified(mock_crawler):
    """Test function docstring."""
    handler = IndexingHandler(mock_crawler)
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/watch/test.pdf"
    
    handler.on_modified(event)
    mock_crawler._process_file.assert_called_once_with(Path("/tmp/watch/test.pdf"), 0)

def test_indexing_handler_on_modified_unsupported(mock_crawler):
    """Test function docstring."""
    handler = IndexingHandler(mock_crawler)
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/watch/test.exe"
    
    handler.on_modified(event)
    assert not mock_crawler._process_file.called

def test_indexing_handler_on_created(mock_crawler):
    """Test function docstring."""
    handler = IndexingHandler(mock_crawler)
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/watch/test.md"
    
    handler.on_created(event)
    mock_crawler._process_file.assert_called_once_with(Path("/tmp/watch/test.md"), 0)

def test_watcher_start(mock_crawler):
    """Test function docstring."""
    with patch("mcp_university.crawler.watcher.Observer") as mock_observer_class:
        mock_observer = mock_observer_class.return_value
        watcher = Watcher(mock_crawler)
        
        with patch("pathlib.Path.exists", return_value=True):
            # We need to stop the infinite loop in start()
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                watcher.start()
        
        assert mock_observer.schedule.called
        assert mock_observer.start.called
        assert mock_observer.stop.called
