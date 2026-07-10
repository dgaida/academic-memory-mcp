"""Tests for extended features of EmailSearchEngine, including recipient indexing, caching and speed."""

import pytest
import yaml
from pathlib import Path
from datetime import datetime
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

        # Test-E-Mails hinzufügen mit verschiedenen 'to' Typen
        engine.index = [
            {
                "subject": "Frage zur Thesis",
                "from": "user@th-koeln.de",
                "from_name": "Daniel Gaida",
                "to": [{"name": "Max Mustermann", "email": "max@mustermann.de"}, "StringRecipient"],
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

        # Suche nach String-Empfänger
        results = engine.search("StringRecipient")
        assert len(results) == 1

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

        # Erneute Suche (stripped_query already in cache check)
        engine.search("EinSehrSpezifischerSuchbegriff")

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

def test_default_cache_initialization_no_file(mock_config: MagicMock) -> None:
    """Testet das Verhalten wenn cache_file nicht übergeben wird."""
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine()
        assert engine.cache_file == mock_config.data_dir / "cache" / "email_search_cache.json"

def test_load_cache_io_error(mock_config: MagicMock) -> None:
    """Testet, ob Exception beim Laden des Caches abgefangen wird."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    cache_file.write_text("{invalid json")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        assert engine.index == []

def test_save_cache_error(mock_config: MagicMock) -> None:
    """Testet, ob Exception beim Speichern des Caches abgefangen wird."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        with patch("builtins.open", side_effect=IOError("Write failed")):
            engine._save_cache()  # Sollte fehlschlagen, aber Exception abfangen

def test_load_suggestions_cache_io_error(mock_config: MagicMock) -> None:
    """Testet, ob Exception beim Laden des Vorschlags-Caches abgefangen wird."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    suggestions_file = mock_config.data_dir / "cache" / "suggestions_cache.json"
    suggestions_file.write_text("{invalid json")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        # suggestions_cache should fall back to default university terms
        assert "Informatik" in engine.suggestions_cache

def test_save_suggestions_cache_error(mock_config: MagicMock) -> None:
    """Testet, ob Exception beim Speichern des Vorschlags-Caches abgefangen wird."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        with patch("builtins.open", side_effect=IOError("Write failed")):
            engine._save_suggestions_cache()  # Sollte fehlschlagen, aber Exception abfangen

def test_get_search_paths_file_not_found(mock_config: MagicMock) -> None:
    """Testet get_search_paths wenn keine Konfigurationsdateien vorhanden sind."""
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=mock_config.data_dir / "cache" / "test_cache.json")
        paths = engine.get_search_paths()
        assert paths == []

def test_get_search_paths_with_yaml(mock_config: MagicMock) -> None:
    """Testet get_search_paths mit gültigen classifier_paths und train_test_folders Yaml-Dateien."""
    cp_path = mock_config.config_dir / "classifier_paths.yaml"
    p_to_create = mock_config.data_dir / "some_class_path"
    p_to_create.mkdir(parents=True, exist_ok=True)

    with open(cp_path, "w", encoding="utf-8") as f:
        yaml.dump({"class_paths": {"classA": str(p_to_create)}}, f)

    ttf_path = mock_config.config_dir / "train_test_folders.yaml"
    train_to_create = mock_config.config_dir.parent / "train"
    train_to_create.mkdir(parents=True, exist_ok=True)
    with open(ttf_path, "w", encoding="utf-8") as f:
        yaml.dump({"train_path": "train"}, f)

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=mock_config.data_dir / "cache" / "test_cache.json")
        paths = engine.get_search_paths()
        assert str(p_to_create) in [str(p) for p in paths]
        assert str(train_to_create) in [str(p) for p in paths]

def test_get_search_paths_yaml_errors(mock_config: MagicMock) -> None:
    """Testet get_search_paths bei Fehlern beim Yaml-Parsen."""
    cp_path = mock_config.config_dir / "classifier_paths.yaml"
    cp_path.write_text("invalid: [yaml: file")

    ttf_path = mock_config.config_dir / "train_test_folders.yaml"
    ttf_path.write_text("invalid: [yaml: file2")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=mock_config.data_dir / "cache" / "test_cache.json")
        paths = engine.get_search_paths()
        assert paths == []

def test_update_index_force(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet update_index mit force=True."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    p = tmp_path / "Inbox"
    p.mkdir()
    f1 = p / "mail1.eml"
    f1.write_text("Subject: test1")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config), \
         patch.object(EmailSearchEngine, "get_search_paths", return_value=[p]), \
         patch("mcp_university.utils.email_search.MailParser") as mock_parser_cls:

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_details.return_value = {
            "subject": "test1", "from_email": "a@b.com", "from_name": "A", "to": [], "date": datetime(2026, 1, 1)
        }

        engine = EmailSearchEngine(cache_file=cache_file)
        engine.index = [{"path": str(f1.absolute())}] # Already indexed

        # Without force, f1 is skipped
        engine.update_index(force=False)
        assert len(engine.index) == 1
        assert "subject" not in engine.index[0]

        # With force, f1 is re-indexed
        engine.update_index(force=True)
        assert len(engine.index) == 1
        assert engine.index[0]["subject"] == "test1"

def test_update_index_non_datetime_date(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet update_index, wenn das Datum keine datetime Instanz ist."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    p = tmp_path / "Inbox"
    p.mkdir()
    f1 = p / "mail1.eml"
    f1.write_text("Subject: test1")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config), \
         patch.object(EmailSearchEngine, "get_search_paths", return_value=[p]), \
         patch("mcp_university.utils.email_search.MailParser") as mock_parser_cls:

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_details.return_value = {
            "subject": "test1", "from_email": "a@b.com", "from_name": "A", "to": [], "date": "2026-01-01"
        }

        engine = EmailSearchEngine(cache_file=cache_file)
        engine.update_index(force=True)
        assert len(engine.index) == 1
        assert engine.index[0]["date"] == "2026-01-01"

def test_update_index_exception(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet update_index, wenn ein Parser Fehler auftritt."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    p = tmp_path / "Inbox"
    p.mkdir()
    f1 = p / "mail1.eml"
    f1.write_text("Subject: test1")

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config), \
         patch.object(EmailSearchEngine, "get_search_paths", return_value=[p]), \
         patch("mcp_university.utils.email_search.MailParser") as mock_parser_cls:

        mock_parser = mock_parser_cls.return_value
        mock_parser.get_email_details.side_effect = Exception("Parse failed")

        engine = EmailSearchEngine(cache_file=cache_file)
        engine.update_index(force=True)
        assert len(engine.index) == 0 # skipped due to Exception

def test_get_suggestions_short_query(mock_config: MagicMock) -> None:
    """Testet get_suggestions mit kurzer Eingabe."""
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine()
        assert engine.get_suggestions("") == []
        assert engine.get_suggestions("a") == []

def test_get_suggestions_detailed_matching(mock_config: MagicMock) -> None:
    """Testet die differenzierte Extraktion von Begriffen in get_suggestions."""
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"
    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)
        engine.suggestions_cache = set()

        engine.index = [
            {
                "subject": "Die Prüfung wird verschoben",
                "from": "sender@th-koeln.de",
                "from_name": "Peter Schmidt",
                "to": [{"name": "Erich", "email": "erich@th.de"}, "StringRecipient"],
                "date": "2026-01-01"
            }
        ]

        # Testet passendes subject word ("Prüfung" via "Prüf")
        suggs = engine.get_suggestions("Prüf")
        assert "Prüfung" in suggs

        # Testet passender from name ("Peter" via "Pete")
        suggs = engine.get_suggestions("Pete")
        assert "Peter Schmidt" in suggs

        # Testet passender from email ("sender" via "send")
        suggs = engine.get_suggestions("send")
        assert "sender@th-koeln.de" in suggs

        # Testet passender dict to ("Erich" via "Eric")
        suggs = engine.get_suggestions("Eric")
        assert "Erich" in suggs
        assert "erich@th.de" in suggs

        # Testet passender string to ("StringRecipient" via "Recip")
        suggs = engine.get_suggestions("Recip")
        assert "StringRecipient" in suggs

if __name__ == "__main__":
    pytest.main([__file__])
