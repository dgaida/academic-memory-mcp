"""Tests for test_profiler_sources.py."""
import pytest
from datetime import datetime
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_store():
    """Test function docstring."""
    store = MagicMock()
    return store

@pytest.fixture
def mock_profile_store():
    """Test function docstring."""
    store = MagicMock()
    return store

@pytest.fixture
def profiler(mock_store, mock_profile_store, tmp_path):
    """Test function docstring."""
    with patch('mcp_university.summarizer.profiler.MetadataStore', return_value=mock_store):
        with patch('mcp_university.summarizer.profiler.ProfileStore', return_value=mock_profile_store):
            with patch('mcp_university.summarizer.profiler.LLMClientWrapper') as mock_llm:
                with patch('mcp_university.summarizer.profiler.MailParser'):
                    p = PersonProfiler(storage_path=tmp_path)
                    p.llm = mock_llm.return_value
                    yield p

def test_generate_profile_includes_sources(profiler, mock_store):
    """Test function docstring."""
    email = "test@example.com"

    # Mock emails
    emails = [
        {"path": Path("/data/folder1/mail1.msg"), "details": {"date": "2023-01-01", "subject": "S1", "body": "B1"}},
        {"path": Path("/data/folder2/mail2.msg"), "details": {"date": "2023-01-02", "subject": "S2", "body": "B2"}}
    ]

    with patch.object(profiler, 'find_emails_for_address', return_value=emails):
        with patch.object(profiler, '_get_knowledge_graph_context', return_value="KG Context"):
            profiler.llm.chat.return_value = {"message": {"content": "# Test Profile\nDetails here."}}

            profile = profiler.generate_profile(email)

            assert "## Quellen" in profile
            assert "- Wissensgraph" in profile
            assert "- Ordner: /data/folder1" in profile
            assert "- Ordner: /data/folder2" in profile

def test_update_profile_updates_sources(profiler, mock_store, mock_profile_store, tmp_path):
    """Test function docstring."""
    email = "test@example.com"
    profile_file = tmp_path / f"{email}.md"

    # Initial profile
    initial_content = "# Test Profile\nDetails here.\n\n## Quellen\n- Wissensgraph\n- Ordner: /data/folder1\n"
    profile_file.write_text(initial_content, encoding="utf-8")
    # Set mtime to past so that 2023 emails are considered 'new'
    past_date = datetime(2022, 1, 1).timestamp()
    os.utime(profile_file, (past_date, past_date))

    # Mock emails
    all_emails = [
        {"path": Path("/data/folder1/mail1.msg"), "details": {"date": "2023-01-01", "subject": "S1", "body": "B1"}},
        {"path": Path("/data/folder2/mail2.msg"), "details": {"date": "2023-01-02", "subject": "S2", "body": "B2"}}
    ]

    with patch.object(profiler, 'find_emails_for_address', return_value=all_emails):
        with patch.object(profiler, '_get_knowledge_graph_context', return_value="KG Context"):
            # Mock profile_store to return only the first mail as processed
            mock_profile_store.get_processed_filenames.return_value = ["mail1.msg"]

            # LLM should receive profile without sources
            def mock_chat(messages):
                prompt = messages[0]["content"]
                assert "## Quellen" not in prompt
                return {"message": {"content": "# Updated Profile\nNew details."}}

            profiler.llm.chat.side_effect = mock_chat

            profile = profiler.update_profile(email)

            assert "# Updated Profile" in profile
            assert "## Quellen" in profile
            assert "- Wissensgraph" in profile
            assert "- Ordner: /data/folder1" in profile
            assert "- Ordner: /data/folder2" in profile

def test_find_emails_includes_cc(profiler):
    """Test function docstring."""
    email = "cc@example.com"

    # Mock mail details
    details = {
        "from_email": "other@example.com",
        "to": [{"email": "to@example.com"}],
        "cc": [{"email": "cc@example.com"}],
        "date": "2023-01-01",
        "subject": "CC Test",
        "body": "Body"
    }

    with patch.object(profiler.mail_parser, '_get_msg_details', return_value=details):
        with patch.object(profiler, 'get_search_paths', return_value=[Path("/test")]):
            with patch.object(Path, 'rglob', return_value=[Path("/test/mail.msg")]):
                emails = profiler.find_emails_for_address(email)
                assert len(emails) == 1
                assert emails[0]["path"] == Path("/test/mail.msg")

def test_find_emails_limit(profiler):
    """Test function docstring."""
    email = "test@example.com"

    # 150 mock emails
    all_files = [Path(f"/test/mail_{i}.msg") for i in range(150)]

    def mock_get_details(path):
        i = int(path.stem.split("_")[1])
        return {
            "from_email": email,
            "to": [],
            "cc": [],
            "date": f"2023-01-{i:02d}" if i < 30 else "2023-02-01",
            "subject": f"Subj {i}",
            "body": "Body"
        }

    with patch.object(profiler.mail_parser, '_get_msg_details', side_effect=mock_get_details):
        with patch.object(profiler, 'get_search_paths', return_value=[Path("/test")]):
            with patch.object(Path, 'rglob', return_value=all_files):
                emails = profiler.find_emails_for_address(email)
                assert len(emails) == 100
