import pytest
from unittest.mock import MagicMock
from datetime import datetime
import sys

# Mock dependencies to avoid import issues
sys.modules['dotenv'] = MagicMock()
sys.modules['yaml'] = MagicMock()

# Import after mocks
from mcp_university.summarizer.profiler import PersonProfiler  # noqa: E402

@pytest.fixture
def profiler():
    config = MagicMock()
    config.user.emails = ["user@th-koeln.de"]
    llm = MagicMock()
    store = MagicMock()
    parser = MagicMock()
    p = PersonProfiler()
    p.config = config
    p.llm = llm
    p.store = store
    p.mail_parser = parser
    return p

def test_determine_honorific_filters_direct_and_ignores_sammelmail(profiler):
    """Checks honorific determination logic: direct mails + ignore sammelmail."""
    emails = [
        # Sammelmail - should be ignored
        {
            "details": {
                "date": datetime(2023, 10, 1),
                "from_email": "person@test.com",
                "to": [{"email": "user@th-koeln.de"}],
                "body": "Hallo zusammen, wir haben ein Meeting.",
                "subject": "Sammel"
            }
        },
        # Direct mail - should be used
        {
            "details": {
                "date": datetime(2023, 10, 2),
                "from_email": "person@test.com",
                "to": [{"email": "user@th-koeln.de"}],
                "body": "Hallo Daniel, kannst du mir helfen?",
                "subject": "Direkt"
            }
        }
    ]

    profiler.llm.chat.return_value = {"message": {"content": "Du"}}

    res = profiler._determine_honorific(emails, "person@test.com")
    assert res == "Du"

    # Verify LLM was called with the correct email content
    assert profiler.llm.chat.call_count == 1
    prompt = profiler.llm.chat.call_args[0][0][0]["content"]
    assert "Direkt" in prompt
    assert "Hallo zusammen" not in prompt

def test_determine_honorific_direct_user_to_person(profiler):
    """Checks that mail from user to person (direct) is considered."""
    emails = [
        {
            "details": {
                "date": datetime(2023, 10, 1),
                "from_email": "user@th-koeln.de",
                "to": [{"email": "person@test.com"}],
                "body": "Wie geht es dir?",
                "subject": "To Person"
            }
        }
    ]
    profiler.llm.chat.return_value = {"message": {"content": "Du"}}
    res = profiler._determine_honorific(emails, "person@test.com")
    assert res == "Du"
    assert profiler.llm.chat.call_count == 1
