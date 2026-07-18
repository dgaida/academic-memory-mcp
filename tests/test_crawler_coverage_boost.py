"""Tests to boost coverage of mcp_university/crawler/crawler.py."""

import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.crawler.crawler import Crawler
from mcp_university.config import Config


@pytest.fixture
def base_crawler_setup():
    """Returns a tuple of (crawler, mocks) for base testing."""
    config = MagicMock()
    config.folders.folders = []
    config.folders.supported_extensions = [".txt", ".eml", ".msg"]
    config.folders.exclude_patterns = ["excluded"]
    config.user.email = "test@example.com"
    config.folders.summarize_emails_individually = False

    store = MagicMock()
    parser = MagicMock()
    summarizer = MagicMock()
    index = MagicMock()

    crawler = Crawler(config, store, parser, summarizer, index)
    return crawler, config, store, parser, summarizer, index


def test_crawl_folder_not_exists(base_crawler_setup, caplog):
    """Test crawl logs a warning if folder does not exist."""
    crawler, config, _, _, _, _ = base_crawler_setup
    config.folders.folders = ["/nonexistent/path"]

    with caplog.at_level(logging.WARNING):
        crawler.crawl()

    assert "Configured folder does not exist" in caplog.text


def test_folder_summary_failure_and_retry(base_crawler_setup, tmp_path):
    """Test folder summary generation failure retry logic and debug files."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup

    # Set up summarizer to return None (failure), then "success" on retry
    summarizer.summarize_folder.side_effect = [None, "recovered summary"]
    store.get_summary.return_value = None

    dir_path = tmp_path / "somedir"
    dir_path.mkdir()

    # We must have files in dir_path so that item_summaries is not empty
    test_file = dir_path / "test.txt"
    test_file.write_text("data")

    # Mock file processing to yield file summary
    store.get_file.return_value = None
    parser.parse.return_value = "parsed"
    summarizer.summarize_file.return_value = "file_summary"

    # We call _process_directory which triggers folder summary generation
    res_summary, changed = crawler._process_directory(dir_path, parent_id=1, relative_path=Path("somedir"))

    assert res_summary == "recovered summary"
    assert changed is True

    # Verify debug files are written
    assert (dir_path / ".folder_summary_items_debug.txt").exists()
    assert (dir_path / ".folder_summary_combined_debug.txt").exists()


def test_folder_summary_failure_write_debug_exception(base_crawler_setup, tmp_path, caplog):
    """Test folder summary generation failure when write_text on debug files raises an exception."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup

    summarizer.summarize_folder.side_effect = [None, "recovered summary"]
    store.get_summary.return_value = None

    dir_path = tmp_path / "somedir"
    dir_path.mkdir()

    # Create file for item summaries
    test_file = dir_path / "test.txt"
    test_file.write_text("data")
    store.get_file.return_value = None
    parser.parse.return_value = "parsed"
    summarizer.summarize_file.return_value = "file_summary"

    # Mock write_text on Path object to raise exception
    with patch("pathlib.Path.write_text", side_effect=IOError("write error")):
        with caplog.at_level(logging.WARNING):
            res_summary, changed = crawler._process_directory(dir_path, parent_id=1, relative_path=Path("somedir"))

    assert res_summary == "recovered summary"
    assert "Failed to write debug files" in caplog.text


def test_folder_summary_final_failure(base_crawler_setup, tmp_path, caplog):
    """Test folder summary generation final failure after retry."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup

    summarizer.summarize_folder.return_value = None
    store.get_summary.return_value = None

    dir_path = tmp_path / "somedir"
    dir_path.mkdir()

    with caplog.at_level(logging.ERROR):
        # Create a file so item_summaries has at least one entry.
        test_file = dir_path / "test.txt"
        test_file.write_text("content")

        # Mock file processing
        store.get_file.return_value = None
        parser.parse.return_value = "parsed"
        summarizer.summarize_file.return_value = "file_summary"

        res_summary, changed = crawler._process_directory(dir_path, parent_id=1, relative_path=Path("somedir"))

    assert res_summary is None
    assert "Final failure to generate folder summary" in caplog.text


def test_process_email_conversation_no_emails(base_crawler_setup, tmp_path):
    """Test process_email_conversation when no emails exist."""
    crawler, _, _, _, _, _ = base_crawler_setup
    dir_path = tmp_path / "emails"
    dir_path.mkdir()
    (dir_path / "Inbox").mkdir()
    (dir_path / "SentItems").mkdir()

    summary, changed = crawler._process_email_conversation(dir_path, 1, Path("emails"))
    assert summary is None
    assert changed is False


def test_process_email_conversation_unchanged(base_crawler_setup, tmp_path):
    """Test process_email_conversation when conversation is unchanged."""
    crawler, _, store, _, _, _ = base_crawler_setup
    dir_path = tmp_path / "emails"
    dir_path.mkdir()
    inbox = dir_path / "Inbox"
    inbox.mkdir()

    email = inbox / "mail1.eml"
    email.write_text("subject: hello")

    # Mock store to return matching combined hash
    mock_conn = MagicMock()
    store._get_connection.return_value = mock_conn

    # Mock database to return the matching hash
    combined_data = f"{email.name}:{email.stat().st_mtime}:{email.stat().st_size}|"
    import hashlib
    expected_hash = hashlib.sha256(combined_data.encode()).hexdigest()
    mock_conn.execute.return_value.fetchone.return_value = (expected_hash,)

    # Summary file exists
    summary_file = dir_path / ".emails_summary.md"
    summary_file.write_text("existing summary content")

    summary, changed = crawler._process_email_conversation(dir_path, 1, Path("emails"))
    assert summary == "existing summary content"
    assert changed is False


def test_process_email_conversation_success(base_crawler_setup, tmp_path):
    """Test process_email_conversation success logic including fallback counterparts and save exception."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup
    config.folders.summarize_emails_individually = True

    dir_path = tmp_path / "emails"
    dir_path.mkdir()
    inbox = dir_path / "Inbox"
    inbox.mkdir()
    sent = dir_path / "SentItems"
    sent.mkdir()

    mail1 = inbox / "mail1.eml"
    mail1.write_text("email")
    mail2 = sent / "mail2.msg"
    mail2.write_text("email")

    # Mock parser mail parsing details
    # Counterparts fallbacks: cover line 232 (from_name fallback when from_email is missing or matches user_email)
    parser.mail_parser.get_email_details.side_effect = [
        {
            "from_email": None,
            "from_name": "Student One",
            "date": "2030-01-01",
            "to": [],
            "cc": []
        },
        {
            "from_email": "test@example.com", # user_email
            "from_name": "Me",
            "date": "2030-01-02",
            "to": [{"email": "student2@example.com", "name": "Student Two"}],
            "cc": [{"email": "", "name": "Student Three"}]
        }
    ]

    # Mock parsing and summarization
    parser.mail_parser.parse.return_value = "parsed content"
    summarizer.summarize_file.return_value = "individual summary"
    summarizer.summarize_email_conversation.return_value = "combined conversation summary"

    # Mock DB connection
    mock_conn = MagicMock()
    store._get_connection.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = ("different_hash",)

    summary, changed = crawler._process_email_conversation(dir_path, 1, Path("emails"))
    assert "combined conversation summary" in summary
    assert changed is True


def test_process_email_conversation_save_exception(base_crawler_setup, tmp_path, caplog):
    """Test process_email_conversation exception path during write_text."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup

    dir_path = tmp_path / "emails"
    dir_path.mkdir()
    inbox = dir_path / "Inbox"
    inbox.mkdir()
    mail1 = inbox / "mail1.eml"
    mail1.write_text("email")

    parser.mail_parser.get_email_details.return_value = {
        "from_email": "student@example.com",
        "from_name": "",
        "date": "2030-01-01",
        "to": [],
        "cc": []
    }
    parser.mail_parser.parse.return_value = "parsed"
    summarizer.summarize_email_conversation.return_value = "summary"

    mock_conn = MagicMock()
    store._get_connection.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = None

    # Mock path write_text to raise exception
    with patch("pathlib.Path.write_text", side_effect=IOError("Permission denied")):
        with caplog.at_level(logging.ERROR):
            summary, changed = crawler._process_email_conversation(dir_path, 1, Path("emails"))

    assert "Failed to save email summary" in caplog.text


def test_process_email_conversation_no_summaries(base_crawler_setup, tmp_path):
    """Test process_email_conversation when no summaries could be generated."""
    crawler, config, store, parser, summarizer, index = base_crawler_setup

    dir_path = tmp_path / "emails"
    dir_path.mkdir()
    inbox = dir_path / "Inbox"
    inbox.mkdir()
    mail1 = inbox / "mail1.eml"
    mail1.write_text("email")

    parser.mail_parser.get_email_details.return_value = {
        "from_email": "student@example.com",
        "from_name": "",
        "date": "2030-01-01",
        "to": [],
        "cc": []
    }
    parser.mail_parser.parse.return_value = "parsed"
    summarizer.summarize_email_conversation.return_value = None

    mock_conn = MagicMock()
    store._get_connection.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = None

    summary, changed = crawler._process_email_conversation(dir_path, 1, Path("emails"))
    assert summary is None
    assert changed is False


def test_process_file_failures(base_crawler_setup, tmp_path):
    """Test _process_file when parser or summarizer returns None."""
    crawler, _, store, parser, summarizer, _ = base_crawler_setup
    store.get_file.return_value = None

    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    # 1. Parser fails
    parser.parse.return_value = None
    summary, changed = crawler._process_file(file_path, 1)
    assert summary is None
    assert changed is False

    # 2. Summarizer fails
    parser.parse.return_value = "parsed content"
    summarizer.summarize_file.return_value = None
    summary, changed = crawler._process_file(file_path, 1)
    assert summary is None
    assert changed is False


def test_save_summary_to_file_missing_and_exception(base_crawler_setup, tmp_path, caplog):
    """Test _save_summary_to_file when write fails or file missing."""
    crawler, _, _, _, _, _ = base_crawler_setup

    # 1. File missing after write attempt
    dir_path = tmp_path / "folder"
    dir_path.mkdir()

    with patch("pathlib.Path.exists", return_value=False):
        with caplog.at_level(logging.ERROR):
            crawler._save_summary_to_file(dir_path, "summary", parent_id=1)
            assert "Summary file missing after write attempt" in caplog.text

    # 2. Exception raised during write
    with patch("pathlib.Path.write_text", side_effect=IOError("Read-only file system")):
        with caplog.at_level(logging.ERROR):
            crawler._save_summary_to_file(dir_path, "summary", parent_id=1)
            assert "Failed to save folder summary" in caplog.text
