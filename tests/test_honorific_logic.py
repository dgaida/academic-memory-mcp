import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_profiler():
    with patch('mcp_university.summarizer.profiler.get_config') as mock_get:
        cfg = MagicMock()
        cfg.data_dir = Path("/tmp/data")
        cfg.sqlite_path = Path("/tmp/test.db")
        cfg.user.emails = []
        mock_get.return_value = cfg

        with patch('mcp_university.summarizer.profiler.MetadataStore'), \
             patch('mcp_university.summarizer.profiler.MailParser'), \
             patch('mcp_university.summarizer.profiler.LLMClientWrapper') as mock_llm_wrapper, \
             patch('mcp_university.summarizer.profiler.ProfileStore'):

            profiler = PersonProfiler(storage_path=Path("/tmp/steckbriefe"))
            profiler.llm = MagicMock()
            yield profiler

def test_honorific_transition(mock_profiler):
    """3 emails provided; the oldest two result in 'Sie', the newest in 'Du'. Should return 'Du'."""
    now = datetime.now()
    emails = [
        {"details": {"date": now - timedelta(days=2), "subject": "Old", "body": "Sie"}, "date": now - timedelta(days=2)},
        {"details": {"date": now - timedelta(days=1), "subject": "Mid", "body": "Sie"}, "date": now - timedelta(days=1)},
        {"details": {"date": now, "subject": "New", "body": "Du"}, "date": now}
    ]

    mock_profiler.llm.chat.side_effect = [
        {"message": {"content": "Du"}},
        {"message": {"content": "Sie"}},
        {"message": {"content": "Sie"}}
    ]

    res = mock_profiler._determine_honorific(emails)
    assert res == "Du"
    assert mock_profiler.llm.chat.call_count == 1

def test_honorific_all_sie(mock_profiler):
    """All 3 emails return 'Sie'."""
    now = datetime.now()
    emails = [
        {"details": {"date": now - timedelta(days=2), "subject": "S1", "body": "S"}, "date": now - timedelta(days=2)},
        {"details": {"date": now - timedelta(days=1), "subject": "S2", "body": "S"}, "date": now - timedelta(days=1)},
        {"details": {"date": now, "subject": "S3", "body": "S"}, "date": now}
    ]

    mock_profiler.llm.chat.side_effect = [
        {"message": {"content": "Sie"}},
        {"message": {"content": "Sie"}},
        {"message": {"content": "Sie"}}
    ]

    res = mock_profiler._determine_honorific(emails)
    assert res == "Sie"
    assert mock_profiler.llm.chat.call_count == 1

def test_honorific_unklar_then_du(mock_profiler):
    """Newest is 'Unklar', next is 'Du'."""
    now = datetime.now()
    emails = [
        {"details": {"date": now - timedelta(days=1), "subject": "D", "body": "D"}, "date": now - timedelta(days=1)},
        {"details": {"date": now, "subject": "U", "body": "U"}, "date": now}
    ]

    mock_profiler.llm.chat.side_effect = [
        {"message": {"content": "Unklar"}},
        {"message": {"content": "Du"}}
    ]

    res = mock_profiler._determine_honorific(emails)
    assert res == "Du"
    assert mock_profiler.llm.chat.call_count == 2

def test_honorific_empty(mock_profiler):
    """No emails -> default to 'Sie'."""
    res = mock_profiler._determine_honorific([])
    assert res == "Sie"
    assert mock_profiler.llm.chat.call_count == 0

def test_honorific_only_3_newest_logic(mock_profiler):
    """Logic should only consider the 3 newest emails."""
    now = datetime.now()
    # 4 emails. The oldest (4th) is 'Du', but the top 3 are 'Unklar'.
    emails = [
        {"details": {"date": now - timedelta(days=10), "body": "Du"}, "date": now - timedelta(days=10)},
        {"details": {"date": now - timedelta(days=2), "body": "U"}, "date": now - timedelta(days=2)},
        {"details": {"date": now - timedelta(days=1), "body": "U"}, "date": now - timedelta(days=1)},
        {"details": {"date": now, "body": "U"}, "date": now}
    ]

    mock_profiler.llm.chat.side_effect = [
        {"message": {"content": "Unklar"}},
        {"message": {"content": "Unklar"}},
        {"message": {"content": "Unklar"}}
    ]

    res = mock_profiler._determine_honorific(emails)
    assert res == "Sie" # Fallback because top 3 were Unklar
    assert mock_profiler.llm.chat.call_count == 3 # 4th mail should NOT be checked
