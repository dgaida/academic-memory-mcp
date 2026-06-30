"""Tests für die EmailSearchEngine."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from mcp_university.utils.email_search import EmailSearchEngine

@pytest.fixture
def mock_config(tmp_path):
    """Erstellt eine gemockte Konfiguration."""
    config = MagicMock()
    config.data_dir = tmp_path / "data"
    config.config_dir = tmp_path / "config"
    config.data_dir.mkdir()
    config.config_dir.mkdir()
    (config.data_dir / "cache").mkdir()
    return config

@pytest.fixture
def search_engine(mock_config, tmp_path):
    """Erstellt eine EmailSearchEngine mit gemockter Konfiguration."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        return engine

def test_add_to_index_and_search(search_engine):
    """Testet das Hinzufügen zum Index und die Suche."""
    test_data = {
        "subject": "Test Email",
        "from": "test@example.com",
        "from_name": "Max Mustermann",
        "date": datetime.now().isoformat(),
        "path": "/path/to/test.msg",
        "filename": "test.msg"
    }
    search_engine.index.append(test_data)

    results = search_engine.search("Max")
    assert len(results) == 1
    assert results[0]["from_name"] == "Max Mustermann"

    results = search_engine.search("Test")
    assert len(results) == 1

    results = search_engine.search("Nix")
    assert len(results) == 0

def test_suggestions(search_engine):
    """Testet die Vorschlagsfunktion."""
    test_data = [
        {
            "subject": "Vorlesung Informatik",
            "from": "prof@th-koeln.de",
            "from_name": "Prof. Dr. Schmidt",
            "date": datetime.now().isoformat(),
            "path": "/path/1",
            "filename": "1.msg"
        },
        {
            "subject": "Prüfungstermin",
            "from": "sekretariat@th-koeln.de",
            "from_name": "Sekretariat",
            "date": datetime.now().isoformat(),
            "path": "/path/2",
            "filename": "2.msg"
        }
    ]
    search_engine.index.extend(test_data)

    suggestions = search_engine.get_suggestions("Prof")
    assert "Prof. Dr. Schmidt" in suggestions

    suggestions = search_engine.get_suggestions("Sekr")
    assert "Sekretariat" in suggestions

    suggestions = search_engine.get_suggestions("Info")
    assert "Informatik" in suggestions

def test_cache_persistence(mock_config, tmp_path):
    """Testet die Persistenz des Caches."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine1 = EmailSearchEngine(cache_file=cache_file)
        engine1.index.append({
            "subject": "Cached Email",
            "from": "cache@example.com",
            "from_name": "Cache Man",
            "date": datetime.now().isoformat(),
            "path": "/path/cache.msg",
            "filename": "cache.msg"
        })
        engine1._save_cache()

        engine2 = EmailSearchEngine(cache_file=cache_file)
        assert len(engine2.index) == 1
        assert engine2.index[0]["subject"] == "Cached Email"
