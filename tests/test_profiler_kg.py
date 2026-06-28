"""Tests für den PersonProfiler mit Knowledge Graph Integration."""
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

def test_get_kg_info(profiler):
    """Testet das Abrufen von Informationen aus dem Knowledge Graph.

    Args:
        profiler: Der Test-Profiler.
    """
    mock_db = MagicMock()
    mock_db.get_person_by_email.return_value = {"name": "Max Mustermann", "role": "Student"}

    with patch("mcp_university.summarizer.profiler.MetadataStore", return_value=mock_db):
        info = profiler._get_kg_info("max@mustermann.de")
        assert info["name"] == "Max Mustermann"
        assert info["role"] == "Student"

def test_get_kg_info_by_name(profiler):
    """Testet das Abrufen von Informationen aus dem KG basierend auf dem Namen.

    Args:
        profiler: Der Test-Profiler.
    """
    mock_db = MagicMock()
    mock_db.get_person_by_email.return_value = None
    mock_db.get_person_by_name.return_value = {"name": "Max Mustermann", "role": "Student"}

    with patch("mcp_university.summarizer.profiler.MetadataStore", return_value=mock_db):
        info = profiler._get_kg_info("max@mustermann.de", name="Max Mustermann")
        assert info["name"] == "Max Mustermann"
