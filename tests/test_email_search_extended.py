"""Tests for extended features of EmailSearchEngine, including recipient indexing, caching and speed."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.utils.email_search import EmailSearchEngine

@pytest.fixture
def mock_config(tmp_path: Path) -> MagicMock:
    """Erstellt eine gemockte Konfiguration für Tests.

    Args:
        tmp_path (Path): Temporärer Pfad für Tests.

    Returns:
        MagicMock: Die gemockte Konfiguration.
    """
    config = MagicMock()
    config.data_dir = tmp_path / "data"
    config.config_dir = tmp_path / "config"
    config.data_dir.mkdir()
    config.config_dir.mkdir()
    (config.data_dir / "cache").mkdir()
    return config

def test_sent_items_detection_various_names(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet die Erkennung verschiedener Namen für gesendete Elemente.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.
        tmp_path (Path): Temporärer Pfad für Tests.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    folder_names = ["SentItems", "Sent Items", "Gesendete Elemente", "Gesendete Objekte", "Sent", "sentitems", "sent"]
    search_paths = []

    for idx, folder_name in enumerate(folder_names):
        folder_path = tmp_path / folder_name
        folder_path.mkdir()
        file = folder_path / f"test_{idx}.eml"
        file.write_text(f"From: me@example.com\nSubject: Mail in {folder_name}\n\nBody")
        search_paths.append(folder_path)

    inbox_path = tmp_path / "Inbox"
    inbox_path.mkdir()
    inbox_file = inbox_path / "test_inbox.eml"
    inbox_file.write_text("From: someone@example.com\nSubject: Inbox Mail\n\nBody")
    search_paths.append(inbox_path)

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config), \
         patch.object(EmailSearchEngine, "get_search_paths", return_value=search_paths):

        engine = EmailSearchEngine(cache_file=cache_file)
        engine.update_index()

        sent_results = [item for item in engine.index if item["folder"] == "SentItems"]
        inbox_results = [item for item in engine.index if item["folder"] == "Inbox"]

        assert len(sent_results) == len(folder_names)
        assert len(inbox_results) == 1

        for folder_name in folder_names:
            assert any(item["subject"] == f"Mail in {folder_name}" for item in sent_results)

def test_recipient_indexing_and_searching(mock_config: MagicMock) -> None:
    """Testet, ob Empfänger indiziert und erfolgreich gesucht werden können.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        # Test-E-Mails hinzufügen
        engine.index = [
            {
                "subject": "Frage zur Thesis",
                "from": "user@th-koeln.de",
                "from_name": "Daniel Gaida",
                "to": [{"name": "Max Mustermann", "email": "max@mustermann.de"}],
                "date": "2026-07-09T18:00:00",
                "path": "/path/to/sent/thesis.eml",
                "filename": "thesis.eml",
                "folder": "SentItems"
            },
            {
                "subject": "Anderer Betreff",
                "from": "someone@example.com",
                "from_name": "Susi Sorglos",
                "to": [{"name": "Erika Musterfrau", "email": "erika@musterfrau.de"}],
                "date": "2026-07-09T18:30:00",
                "path": "/path/to/inbox/other.eml",
                "filename": "other.eml",
                "folder": "Inbox"
            }
        ]

        # Suche nach Name des Empfängers (Mustermann)
        results = engine.search("Mustermann")
        assert len(results) == 1
        assert results[0]["to"][0]["name"] == "Max Mustermann"

        # Suche nach E-Mail des Empfängers
        results = engine.search("musterfrau.de")
        assert len(results) == 1
        assert results[0]["to"][0]["name"] == "Erika Musterfrau"

        # Suche nach Ordnerpfad-Teil
        results = engine.search("inbox")
        assert len(results) == 1
        assert results[0]["filename"] == "other.eml"

def test_suggestions_cache_loading_and_saving(mock_config: MagicMock) -> None:
    """Testet das Laden, die Default-Werte und das Speichern des Vorschlags-Caches.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    suggestions_file = mock_config.data_dir / "cache" / "suggestions_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        # Standard-Begriffe müssen im Cache vorhanden sein
        assert "Informatik" in engine.suggestions_cache
        assert "Bachelorarbeit" in engine.suggestions_cache
        assert suggestions_file.exists()

        # Vorschläge abfragen
        suggestions = engine.get_suggestions("Info")
        assert len(suggestions) > 0
        assert any("Informatik" in s for s in suggestions)

def test_dynamic_cache_extension(mock_config: MagicMock) -> None:
    """Testet, ob neue Suchbegriffe dynamisch zum Vorschlags-Cache hinzugefügt werden.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        # Begriff ist noch nicht im Cache
        assert "EinSehrSpezifischerSuchbegriff" not in engine.suggestions_cache

        # Suche ausführen
        engine.search("EinSehrSpezifischerSuchbegriff")

        # Jetzt muss er im Cache sein und persistiert
        assert "EinSehrSpezifischerSuchbegriff" in engine.suggestions_cache

        # Suche nach einem kurzen Begriff (sollte nicht gespeichert werden)
        engine.search("x")
        assert "x" not in engine.suggestions_cache

def test_fast_suggestions_filtering(mock_config: MagicMock) -> None:
    """Testet das schnelle Filtern und die Priorisierung von Präfixen im Vorschlags-Cache.

    Args:
        mock_config (MagicMock): Die gemockte Konfiguration.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        # Spezielle Testdaten in den Cache setzen
        engine.suggestions_cache = {
            "Anmeldung Masterarbeit",
            "Master-Studiengang",
            "Lehrveranstaltung Master",
            "Klausur"
        }

        # Vorschläge für "Master" holen
        suggestions = engine.get_suggestions("Master")

        # "Master-Studiengang" sollte vor "Anmeldung Masterarbeit" und "Lehrveranstaltung Master" einsortiert werden
        # da es mit "Master" beginnt (Präfix-Priorisierung)
        assert suggestions[0] == "Master-Studiengang"
        assert len(suggestions) == 3

if __name__ == "__main__":
    pytest.main([__file__])
