"""Tests für die Datenquellen des PersonProfilers."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def profiler():
    """Erstellt einen PersonProfiler mit gemockten Abhängigkeiten.

    Returns:
        PersonProfiler: Der initialisierte Profiler.
    """
    with patch("mcp_university.summarizer.profiler.get_config"):
        return PersonProfiler()

def test_collect_emails(profiler):
    """Testet das Sammeln von E-Mails für ein Profil.

    Args:
        profiler: Der Test-Profiler.
    """
    mock_files = [MagicMock(), MagicMock()]
    with patch("pathlib.Path.rglob", return_value=mock_files):
        emails = profiler._collect_emails("max@mustermann.de")
        assert len(emails) == 2

def test_collect_emails_limit(profiler):
    """Testet das Limit beim Sammeln von E-Mails.

    Args:
        profiler: Der Test-Profiler.
    """
    mock_files = [MagicMock() for _ in range(150)]
    with patch("pathlib.Path.rglob", return_value=mock_files):
        emails = profiler._collect_emails("max@mustermann.de")
        assert len(emails) == 100
