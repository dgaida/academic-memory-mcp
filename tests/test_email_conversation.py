import pytest
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
    config.user = UserConfig(name="Daniel Gaida", email="daniel.gaida@th-koeln.de")

    store = MetadataStore(tmp_path / "test.db")
    parser = ParserFactory(tmp_path / "cache")
    summarizer = MagicMock(spec=Summarizer)
    index = MagicMock(spec=SearchIndex)

    # Default returns to avoid sqlite errors with MagicMocks
    summarizer.summarize_file.return_value = "# File Summary"
    summarizer.summarize_folder.return_value = "# Folder Summary"
    summarizer.summarize_email_conversation.return_value = "# Conversation Summary"

    return config, store, parser, summarizer, index

def test_email_conversation_processing(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps

    # Create structure
    student_dir = tmp_path / "StudentX"
    inbox = student_dir / "Inbox"
    sent = student_dir / "SentItems"
    inbox.mkdir(parents=True)
    sent.mkdir()

    # Create emails
    mail1 = inbox / "1.eml"
    mail1.write_text("Date: Mon, 1 Jan 2024 10:00:00 +0000\nFrom: User <other@example.com>\nTo: Daniel Gaida <daniel.gaida@th-koeln.de>\n\nQuestion")

    mail2 = sent / "2.eml"
    mail2.write_text("Date: Tue, 2 Jan 2024 10:00:00 +0000\nFrom: Daniel Gaida <daniel.gaida@th-koeln.de>\nTo: User <other@example.com>\n\nAnswer")

    crawler = Crawler(config, store, parser, summarizer, index)
    crawler.crawl()

    # Check if summary file exists (reverted filename)
    summary_file = student_dir / ".emails_summary.md"
    assert summary_file.exists()
    assert summary_file.read_text() == "# Conversation Summary"

    # Check if individual emails are NOT indexed as files
    with store._get_connection() as conn:
        files = conn.execute("SELECT path FROM files").fetchall()
        for f in files:
            assert "Inbox" not in f[0]
            assert "SentItems" not in f[0]

    # Check if conversation summary is indexed
    # Extract actual call for better matching
    args, kwargs = index.add_document.call_args
    assert args[0] == str(summary_file)
    assert args[1] == "# Conversation Summary"
    assert args[2]["is_conversation_summary"] == "true"
    assert args[2]["filename"] == ".emails_summary.md"

def test_email_sorting(tmp_path, mock_deps):
    config, store, parser, summarizer, index = mock_deps

    # Create structure
    student_dir = tmp_path / "StudentY"
    inbox = student_dir / "Inbox"
    sent = student_dir / "SentItems"
    inbox.mkdir(parents=True)
    sent.mkdir()

    # Create emails out of order
    mail2 = sent / "2.eml"
    mail2.write_text("Date: Tue, 2 Jan 2024 10:00:00 +0000\nFrom: Daniel Gaida <daniel.gaida@th-koeln.de>\nTo: User <other@example.com>\n\nLater")

    mail1 = inbox / "1.eml"
    mail1.write_text("Date: Mon, 1 Jan 2024 10:00:00 +0000\nFrom: User <other@example.com>\nTo: Daniel Gaida <daniel.gaida@th-koeln.de>\n\nEarlier")

    crawler = Crawler(config, store, parser, summarizer, index)

    # Capture the text passed to summarize_email_conversation
    crawler.crawl()

    args, _ = summarizer.summarize_email_conversation.call_args
    content = args[1]

    # Check order (should be newest first)
    pos1 = content.find("Earlier")
    pos2 = content.find("Later")
    assert pos1 != -1
    assert pos2 != -1
    assert pos2 < pos1, "Emails should be sorted newest to oldest"
