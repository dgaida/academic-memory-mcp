import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_store():
    store = MagicMock()
    return store

@pytest.fixture
def mock_profile_store():
    store = MagicMock()
    return store

@pytest.fixture
def profiler(mock_store, mock_profile_store, tmp_path):
    with patch('mcp_university.summarizer.profiler.MetadataStore', return_value=mock_store):
        with patch('mcp_university.summarizer.profiler.ProfileStore', return_value=mock_profile_store):
            with patch('mcp_university.summarizer.profiler.LLMClientWrapper') as mock_llm:
                with patch('mcp_university.summarizer.profiler.MailParser'):
                    p = PersonProfiler(storage_path=tmp_path)
                    p.llm = mock_llm.return_value
                    yield p

def test_generate_profile_includes_sources(profiler, mock_store):
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
    email = "test@example.com"
    # profiler.storage_path is already tmp_path from fixture
    profile_file = tmp_path / f"{email}.md"

    # Initial profile
    initial_content = "# Test Profile\nDetails here.\n\n## Quellen\n- Wissensgraph\n- Ordner: /data/folder1\n"
    profile_file.write_text(initial_content, encoding="utf-8")

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
