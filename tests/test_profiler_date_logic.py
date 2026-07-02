import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_store():
    return MagicMock()

@pytest.fixture
def mock_profile_store():
    return MagicMock()

@pytest.fixture
def profiler(mock_store, mock_profile_store, tmp_path):
    with patch('mcp_university.summarizer.profiler.MetadataStore', return_value=mock_store):
        with patch('mcp_university.summarizer.profiler.ProfileStore', return_value=mock_profile_store):
            with patch('mcp_university.summarizer.profiler.LLMClientWrapper') as mock_llm:
                with patch('mcp_university.summarizer.profiler.MailParser'):
                    p = PersonProfiler(storage_path=tmp_path)
                    p.llm = mock_llm.return_value
                    yield p

def test_update_profile_filters_by_date(profiler, mock_profile_store, tmp_path):
    """Testet, ob nur E-Mails verwendet werden, die neuer als die Steckbrief-Datei sind."""
    email = "test@example.com"
    profile_file = tmp_path / f"{email}.md"

    # Steckbrief erstellen und mtime auf vor 1 Stunde setzen
    profile_file.write_text("# Alter Steckbrief", encoding="utf-8")
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    os.utime(profile_file, (one_hour_ago.timestamp(), one_hour_ago.timestamp()))

    # Mock E-Mails: eine alt, eine neu
    old_date = one_hour_ago - timedelta(minutes=30)
    new_date = one_hour_ago + timedelta(minutes=30)

    all_emails = [
        {
            "path": Path("old.msg"),
            "date": old_date,
            "details": {"date": old_date, "subject": "Alt", "body": "Alter Inhalt"}
        },
        {
            "path": Path("new.msg"),
            "date": new_date,
            "details": {"date": new_date, "subject": "Neu", "body": "Neuer Inhalt"}
        }
    ]

    with patch.object(profiler, 'find_emails_for_address', return_value=all_emails):
        mock_profile_store.get_processed_filenames.return_value = set()
        profiler.llm.chat.return_value = {"message": {"content": "# Aktualisierter Steckbrief"}}

        with patch.object(profiler, '_get_knowledge_graph_context', return_value=""):
            with patch.object(profiler, '_get_sources_text', return_value=""):
                with patch.object(profiler, '_determine_honorific', return_value="Sie"):
                    profiler.update_profile(email)

        # Prüfen, was an das LLM gesendet wurde
        calls = profiler.llm.chat.call_args_list
        prompt = calls[0][0][0][0]["content"]

        assert "Neuer Inhalt" in prompt
        assert "Alter Inhalt" not in prompt
