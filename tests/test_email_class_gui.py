"""Tests für die E-Mail-Klassen-GUI und die zugehörigen SearchEngine-Methoden."""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_university.utils.email_search import EmailSearchEngine
from scripts.email_class_gui import (
    open_in_outlook,
    open_in_explorer,
    on_class_change,
    check_steckbrief_status,
    on_address_select,
    generate_steckbrief_action,
    display_email
)


@pytest.fixture
def mock_config(tmp_path: Path) -> MagicMock:
    """Erstellt eine gemockte Konfiguration für Tests.

    Args:
        tmp_path (Path): Temporärer Pfad für Tests.

    Returns:
        MagicMock: Gemockte Konfiguration.
    """
    config = MagicMock()
    config.data_dir = tmp_path / "data"
    config.config_dir = tmp_path / "config"
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.config_dir.mkdir(parents=True, exist_ok=True)
    (config.data_dir / "cache").mkdir(parents=True, exist_ok=True)
    config.user.emails = ["daniel.gaida@th-koeln.de"]
    return config


def test_determine_email_class_and_get_classes(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet determine_email_class und get_email_classes.

    Args:
        mock_config (MagicMock): Gemockte Konfiguration.
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        # Test mit bekannten Pfadstrukturen
        bachelor_file = tmp_path / "BachelorThesis" / "SS2024" / "Mustermann" / "Inbox" / "mail.eml"
        master_file = tmp_path / "MasterThesis" / "Inbox" / "mail.eml"
        unknown_file = tmp_path / "UnbekannterOrdner" / "mail.eml"

        assert engine.determine_email_class(bachelor_file) == "BachelorThesis"
        assert engine.determine_email_class(master_file) == "MasterThesis"
        assert engine.determine_email_class(unknown_file) == "Sonstiges"

        # Index mit Testdaten befüllen
        engine.index = [
            {
                "subject": "Bachelor Arbeit Frage",
                "from": "student@smail.th-koeln.de",
                "from_name": "Max Mustermann",
                "to": [{"name": "Daniel Gaida", "email": "daniel.gaida@th-koeln.de"}],
                "date": "2026-05-10T10:00:00",
                "path": str(bachelor_file),
                "filename": "mail.eml",
                "folder": "Inbox",
                "email_class": "BachelorThesis"
            },
            {
                "subject": "Master Thesis Update",
                "from": "daniel.gaida@th-koeln.de",
                "from_name": "Daniel Gaida",
                "to": [{"name": "Erika Musterfrau", "email": "erika@smail.th-koeln.de"}],
                "date": "2026-05-11T12:00:00",
                "path": str(master_file),
                "filename": "mail.eml",
                "folder": "SentItems",
                "email_class": "MasterThesis"
            }
        ]

        classes = engine.get_email_classes()
        assert "BachelorThesis" in classes
        assert "MasterThesis" in classes


def test_get_addresses_and_emails_for_class(mock_config: MagicMock, tmp_path: Path) -> None:
    """Testet get_addresses_for_class und get_emails_for_class_and_address.

    Args:
        mock_config (MagicMock): Gemockte Konfiguration.
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    cache_file = mock_config.data_dir / "cache" / "test_cache.json"

    with patch("mcp_university.utils.email_search.get_config", return_value=mock_config):
        engine = EmailSearchEngine(cache_file=cache_file)

        bachelor_inbox = str(tmp_path / "BachelorThesis" / "Inbox" / "mail1.eml")
        bachelor_sent = str(tmp_path / "BachelorThesis" / "SentItems" / "mail2.eml")

        engine.index = [
            {
                "subject": "Frage zu Bachelor",
                "from": "student@smail.th-koeln.de",
                "from_name": "Max Mustermann",
                "to": [{"name": "Daniel Gaida", "email": "daniel.gaida@th-koeln.de"}],
                "date": "2026-05-10T10:00:00",
                "path": bachelor_inbox,
                "filename": "mail1.eml",
                "folder": "Inbox",
                "email_class": "BachelorThesis"
            },
            {
                "subject": "Antwort zu Bachelor",
                "from": "daniel.gaida@th-koeln.de",
                "from_name": "Daniel Gaida",
                "to": [{"name": "Max Mustermann", "email": "student@smail.th-koeln.de"}],
                "date": "2026-05-10T11:00:00",
                "path": bachelor_sent,
                "filename": "mail2.eml",
                "folder": "SentItems",
                "email_class": "BachelorThesis"
            }
        ]

        # Adressen für BachelorThesis holen
        addrs = engine.get_addresses_for_class("BachelorThesis")
        assert len(addrs) == 1
        assert addrs[0]["email"] == "student@smail.th-koeln.de"
        assert addrs[0]["name"] == "Max Mustermann"
        assert addrs[0]["count"] == 2

        # E-Mails abfragen
        inbox_mails, sent_mails = engine.get_emails_for_class_and_address("BachelorThesis", "student@smail.th-koeln.de")
        assert len(inbox_mails) == 1
        assert len(sent_mails) == 1
        assert inbox_mails[0]["path"] == bachelor_inbox
        assert sent_mails[0]["path"] == bachelor_sent


def test_open_in_outlook_and_explorer(tmp_path: Path) -> None:
    """Testet open_in_outlook und open_in_explorer Hilfsfunktionen.

    Args:
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    # Nicht existierende Datei
    assert "Datei nicht gefunden" in open_in_outlook(str(tmp_path / "non_existing.eml"))
    assert "Datei nicht gefunden" in open_in_explorer(str(tmp_path / "non_existing.eml"))

    # Existierende Datei
    test_file = tmp_path / "test.eml"
    test_file.write_text("Test content")

    with patch("os.startfile", create=True), \
         patch("subprocess.run"), \
         patch("platform.system", return_value="Windows"):
        msg = open_in_outlook(str(test_file))
        assert "Geöffnet" in msg

        msg_exp = open_in_explorer(str(test_file))
        assert "Ordner geöffnet" in msg_exp


@patch("scripts.email_class_gui.GUITools")
def test_on_class_change(mock_gui_tools: MagicMock) -> None:
    """Testet die on_class_change-Funktion der GUI.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.

    Returns:
        None
    """
    # Test bei leerer Auswahl
    res = on_class_change("")
    assert res[0].empty
    assert "Keine E-Mail-Klasse" in res[-1]

    # Test mit gültiger Klasse
    mock_engine = MagicMock()
    mock_engine.get_addresses_for_class.return_value = [
        {"email": "test@example.com", "name": "Test User", "count": 3}
    ]
    mock_gui_tools.engine.return_value = mock_engine

    res_valid = on_class_change("BachelorThesis")
    addr_df = res_valid[0]
    assert len(addr_df) == 1
    assert addr_df.iloc[0]["E-Mail-Adresse"] == "test@example.com"
    assert addr_df.iloc[0]["Anzahl E-Mails"] == 3
    assert "1 E-Mail-Adresse" in res_valid[-1]


@patch("scripts.email_class_gui.GUITools")
def test_check_steckbrief_status(mock_gui_tools: MagicMock, tmp_path: Path) -> None:
    """Testet check_steckbrief_status für vorhandene und fehlende Steckbriefe.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    mock_profiler = MagicMock()
    mock_profiler.storage_path = tmp_path
    mock_gui_tools.profiler.return_value = mock_profiler

    # Test mit leerer E-Mail
    md, btn, status = check_steckbrief_status("")
    assert "Wähle eine E-Mail-Adresse" in md

    # Test wenn Datei nicht existiert
    md_missing, btn_missing, status_missing = check_steckbrief_status("missing@example.com")
    assert "Kein Steckbrief vorhanden" in md_missing
    assert btn_missing.get("visible") is True

    # Test wenn Datei existiert
    profile_file = tmp_path / "existing@example.com.md"
    profile_file.write_text("# Steckbrief von Existing User", encoding="utf-8")

    md_exist, btn_exist, status_exist = check_steckbrief_status("existing@example.com")
    assert "# Steckbrief von Existing User" in md_exist
    assert btn_exist.get("visible") is False


@patch("scripts.email_class_gui.GUITools")
def test_on_address_select(mock_gui_tools: MagicMock, tmp_path: Path) -> None:
    """Testet die on_address_select Funktion.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    mock_profiler = MagicMock()
    mock_profiler.storage_path = tmp_path
    mock_gui_tools.profiler.return_value = mock_profiler

    mock_engine = MagicMock()
    mock_engine.get_emails_for_class_and_address.return_value = (
        [{"date": "2026-05-10", "from_name": "Sender", "subject": "Sub1", "path": "/p1"}],
        [{"date": "2026-05-11", "from_name": "Me", "subject": "Sub2", "path": "/p2"}]
    )
    mock_gui_tools.engine.return_value = mock_engine

    # DataFrame für Adressen vorbereiten
    df_addrs = pd.DataFrame([
        ["Test User", "test@example.com", 2]
    ], columns=["Name", "E-Mail-Adresse", "Anzahl E-Mails"])

    evt = MagicMock()
    evt.index = [0]

    res = on_address_select(evt, df_addrs, "BachelorThesis")
    inbox_df = res[3]
    sent_df = res[4]

    assert len(inbox_df) == 1
    assert len(sent_df) == 1
    assert inbox_df.iloc[0]["Betreff"] == "Sub1"
    assert sent_df.iloc[0]["Betreff"] == "Sub2"
    assert res[5] == "test@example.com"


@patch("scripts.email_class_gui.GUITools")
def test_generate_steckbrief_action(mock_gui_tools: MagicMock) -> None:
    """Testet die generate_steckbrief_action Funktion.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.

    Returns:
        None
    """
    mock_profiler = MagicMock()
    mock_profiler.generate_profile.return_value = "# Steckbrief Inhalt"
    mock_gui_tools.profiler.return_value = mock_profiler

    # Erfolgsfall
    content, btn, status = generate_steckbrief_action("test@example.com")
    assert "# Steckbrief Inhalt" in content
    assert btn.get("visible") is False
    assert "erfolgreich generiert" in status

    # Fehlerfall
    mock_profiler.generate_profile.side_effect = Exception("API Fehler")
    content_err, btn_err, status_err = generate_steckbrief_action("test@example.com")
    assert "Fehler bei Steckbrief-Generierung" in content_err
    assert btn_err.get("visible") is True


@patch("scripts.email_class_gui.GUITools")
def test_display_email(mock_gui_tools: MagicMock, tmp_path: Path) -> None:
    """Testet display_email zur HTML-Darstellung.

    Args:
        mock_gui_tools (MagicMock): Gemockte GUITools.
        tmp_path (Path): Temporärer Pfad.

    Returns:
        None
    """
    mock_parser = MagicMock()
    mock_parser.get_email_details.return_value = {
        "from_name": "Absender",
        "from_email": "absender@example.com",
        "to": [{"name": "Empfänger", "email": "empfaenger@example.com"}],
        "date": "2026-05-10",
        "subject": "Test Betreff",
        "body": "Hallo Welt Inhalts-Text"
    }
    mock_gui_tools.academic_parser.return_value = mock_parser

    df = pd.DataFrame([
        ["2026-05-10", "Absender", "Test Betreff", "/path/to/mail.eml"]
    ], columns=["Datum", "Von", "Betreff", "Pfad"])

    evt = MagicMock()
    evt.index = [0]

    html, path_out, status = display_email(evt, df)

    assert "Absender" in html
    assert "Hallo Welt Inhalts-Text" in html
    assert path_out == "/path/to/mail.eml"
