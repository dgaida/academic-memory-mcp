import pytest
import logging
from unittest.mock import MagicMock
from mcp_university.crawler.crawler import Crawler
from mcp_university.config import Config, FolderConfig, UserConfig
from mcp_university.metadata.store import MetadataStore
from mcp_university.parser.factory import ParserFactory
from mcp_university.summarizer.engine import Summarizer
from mcp_university.retrieval.index import SearchIndex

@pytest.fixture
def mock_deps(tmp_path):
    config = MagicMock(spec=Config)
    config.folders = FolderConfig(folders=[str(tmp_path)])
    config.folders.supported_extensions = [".eml", ".msg", ".md"]
    config.folders.exclude_patterns = ["cache", "test.db"]
    config.folders.summarize_emails_individually = False
    config.user = UserConfig(name='Daniel Gaida', email='daniel.gaida@th-koeln.de')

    store = MetadataStore(tmp_path / "test.db")
    parser = ParserFactory(tmp_path / "cache")
    summarizer = MagicMock(spec=Summarizer)
    index = MagicMock(spec=SearchIndex)

    summarizer.summarize_folder.return_value = "# Folder Summary"
    summarizer.summarize_email_conversation.return_value = "# Conversation Summary"
    summarizer.summarize_file.side_effect = lambda filename, content: f"Summary for {filename}"

    return config, store, parser, summarizer, index

def test_email_conversation_logging(tmp_path, mock_deps, caplog):
    config, store, parser, summarizer, index = mock_deps
    caplog.set_level(logging.INFO)

    student_dir = tmp_path / "StudentX"
    inbox = student_dir / "Inbox"
    sent = student_dir / "SentItems"
    inbox.mkdir(parents=True)
    sent.mkdir()

    mail1 = inbox / "a.eml"
    mail1.write_text("Date: Mon, 1 Jan 2024 10:00:00 +0000\n\nQuestion")

    mail2 = sent / "b.eml"
    mail2.write_text("Date: Tue, 2 Jan 2024 10:00:00 +0000\n\nAnswer")

    crawler = Crawler(config, store, parser, summarizer, index)
    crawler.crawl()

    assert "Order of emails for conversation with Unbekannt:" in caplog.text
    assert "  - a.eml" in caplog.text
    assert "  - b.eml" in caplog.text

def test_individual_email_summarization_option(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps
    config.folders.summarize_emails_individually = True

    student_dir = tmp_path / "StudentY"
    inbox = student_dir / "Inbox"
    sent = student_dir / "SentItems"
    inbox.mkdir(parents=True)
    sent.mkdir()

    mail1 = inbox / "1.eml"
    mail1.write_text("Date: Mon, 1 Jan 2024 10:00:00 +0000\n\nQuestion")

    crawler = Crawler(config, store, parser, summarizer, index)
    crawler.crawl()

    # Verify that summarize_file was called for the email
    # It might be called multiple times (for the folder and the email)
    # We check if 1.eml was among the calls
    found = False
    for call in summarizer.summarize_file.call_args_list:
        if call.args[0] == "1.eml":
            found = True
            break
    assert found, "summarize_file was not called for 1.eml"

    # Also verify that it was NOT called for the conversation summary file (which should be skipped)
    for call in summarizer.summarize_file.call_args_list:
        assert call.args[0] != ".emails_summary.md"

    # Verify content passed to summarize_email_conversation
    args, _ = summarizer.summarize_email_conversation.call_args
    content = args[1]
    assert "Summary for 1.eml" in content
