"""Tests für die erweiterte NiceGUI E-Mail- und Termin-Zentrale (email_class_gui_nicegui.py)."""

from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from scripts.email_class_gui_nicegui import (
    parse_appointments,
    extract_email,
    extract_lastname,
    get_class_from_title,
    open_file,
    open_in_explorer,
    EmailClassApp,
    GUITools
)


@pytest.fixture
def sample_appointments_md(tmp_path: Path) -> Path:
    """Erstellt eine temporäre appointments.md Datei mit Testdaten.

    Args:
        tmp_path (Path): Temporärer Pfad von pytest.

    Returns:
        Path: Pfad zur erstellten Datei.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    content = f"""# Termine der kommenden 4 Wochen

Zeitraum: {today_str} bis {(now + timedelta(days=28)).strftime('%Y-%m-%d')}
Generiert am: {today_str} 10:00:00

| Datum | Uhrzeit | Dauer (Min) | Ort | Thema | Teilnehmer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| {today_str} | 09:00 | 30 | Teams | Bachelor Kolloquium | Max Mustermann <max.mustermann@smail.th-koeln.de> |
| {tomorrow_str} | 14:00 | 60 | Zoom | Projektbesprechung WASP | Erika Musterfrau <erika.musterfrau@th-koeln.de> |
| 2029-01-01 | 10:00 | 45 | Büro | Weit entfernter Termin | Niemand |
"""
    file_path = tmp_path / "appointments.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_parse_appointments_filtering(sample_appointments_md: Path) -> None:
    """Testet das Parsen und Filtern der Termine für die laufende Woche.

    Args:
        sample_appointments_md (Path): Temporäre appointments.md Datei.
    """
    appointments = parse_appointments(sample_appointments_md)
    assert len(appointments) == 2
    assert appointments[0]["subject"] == "Bachelor Kolloquium"
    assert "max.mustermann@smail.th-koeln.de" in appointments[0]["participant"]
    assert appointments[1]["subject"] == "Projektbesprechung WASP"


def test_parse_appointments_fallback_when_none_this_week(tmp_path: Path) -> None:
    """Testet, dass alle Termine zurückgegeben werden, wenn keiner in die Woche fällt.

    Args:
        tmp_path (Path): Temporärer Pfad.
    """
    content = """
| Datum | Uhrzeit | Thema | Teilnehmer |
| :--- | :--- | :--- | :--- |
| 2030-01-01 | 10:00 | Zukunfts-Termin | Test Person <test@test.com> |
"""
    file_path = tmp_path / "future_appointments.md"
    file_path.write_text(content, encoding="utf-8")

    appointments = parse_appointments(file_path)
    assert len(appointments) == 1
    assert appointments[0]["subject"] == "Zukunfts-Termin"


def test_extract_email_and_lastname() -> None:
    """Testet die E-Mail- und Nachnamen-Extraktion."""
    text1 = "Max Mustermann <max.mustermann@smail.th-koeln.de>"
    assert extract_email(text1) == "max.mustermann@smail.th-koeln.de"
    assert extract_lastname(text1) == "Mustermann"

    text2 = "keine-email-adresse"
    assert extract_email(text2) is None


def test_get_class_from_title() -> None:
    """Testet die Bestimmung der E-Mail-Klasse anhand des Titels."""
    class_paths = {
        "BachelorThesis": "D:/Thesen/Bachelor",
        "MasterThesis": "D:/Thesen/Master",
        "WASP": "D:/Projekte/WASP"
    }

    assert get_class_from_title("Kolloquium BachelorThesis Max", class_paths) == "BachelorThesis"
    assert get_class_from_title("Meeting WASP Projekt", class_paths) == "WASP"

    with patch.object(GUITools, "classifier", return_value=None):
        assert get_class_from_title("Allgemeines Treffen", class_paths) == "Other"


def test_open_file_and_explorer(tmp_path: Path) -> None:
    """Testet open_file und open_in_explorer auf Existenzprüfung.

    Args:
        tmp_path (Path): Temporärer Pfad.
    """
    non_existent = tmp_path / "does_not_exist.txt"
    assert "nicht gefunden" in open_file(str(non_existent))
    assert "nicht gefunden" in open_in_explorer(str(non_existent))

    real_file = tmp_path / "real.txt"
    real_file.write_text("Hello World", encoding="utf-8")

    with patch("os.startfile", return_value=None), patch("subprocess.run", return_value=None):
        msg_file = open_file(str(real_file))
        assert "Geöffnet" in msg_file

        msg_folder = open_in_explorer(str(real_file))
        assert "geöffnet" in msg_folder


@pytest.mark.asyncio
async def test_immediate_steckbrief_display(tmp_path: Path) -> None:
    """Testet die Kernanforderung: Sofortige Anzeige existierender Steckbriefe und Hintergrund-Update.

    Args:
        tmp_path (Path): Temporärer Pfad.
    """
    # 1. Existierenden Steckbrief anlegen
    steckbriefe_dir = tmp_path / "Steckbriefe"
    steckbriefe_dir.mkdir()
    email_addr = "max.mustermann@smail.th-koeln.de"
    steckbrief_file = steckbriefe_dir / f"{email_addr}.md"
    initial_content = "### Steckbrief Max Mustermann\n- Studiengang: Informatik"
    steckbrief_file.write_text(initial_content, encoding="utf-8")

    app = EmailClassApp()
    # Mock UI-Elemente
    app.status_label = MagicMock()
    app.app_steckbrief_markdown = MagicMock()
    app.app_steckbrief_status = MagicMock()
    app.app_steckbrief_spinner = MagicMock()
    app.app_steckbrief_refresh_btn = MagicMock()
    app.app_student_folder_label = MagicMock()
    app.app_btn_explorer = MagicMock()
    app.app_summary_refresh_btn = MagicMock()
    app.app_summary_markdown = MagicMock()
    app.app_files_table = MagicMock()

    # Mock profiler mit eigenem Speicherpfad
    mock_profiler = MagicMock()
    mock_profiler.storage_path = steckbriefe_dir
    mock_profiler.update_profile = MagicMock(return_value="### Steckbrief Max Mustermann\n- Studiengang: Informatik\n- Aktualisiert: Ja")

    with patch.object(GUITools, "profiler", return_value=mock_profiler), \
         patch("scripts.email_class_gui_nicegui.get_class_paths", return_value={}):

        row_data = {
            "start": "2026-11-26 09:00",
            "subject": "Besprechung",
            "participant": f"Max Mustermann <{email_addr}>"
        }

        # Ausführen der Selektion
        await app.on_appointment_selected(row_data)

        # PRÜFUNG: Steckbrief muss SOFORT mit dem alten Inhalt angezeigt werden!
        app.app_steckbrief_markdown.set_content.assert_called_with(initial_content)
        assert "sofort geladen" in app.app_steckbrief_status.set_text.call_args[0][0]

        # Hintergrund-Task aufrufen und prüfen ob er aktualisiert
        await app._update_appointment_steckbrief_background(email_addr)
        assert "Aktualisiert: Ja" in app.app_steckbrief_markdown.set_content.call_args[0][0]


@pytest.mark.asyncio
async def test_search_functionality(tmp_path: Path) -> None:
    """Testet die E-Mail-Schnellsuche (Tab 3).

    Args:
        tmp_path (Path): Temporärer Pfad.
    """
    app = EmailClassApp()
    app.status_label = MagicMock()
    app.search_input = MagicMock()
    app.search_input.value = "Klausur"
    app.search_inbox_table = MagicMock()
    app.search_sent_table = MagicMock()
    app.tab3_inbox_label = MagicMock()
    app.tab3_sent_label = MagicMock()

    mock_results = [
        {
            "date": "2026-11-20T10:00:00",
            "from": "student@th-koeln.de",
            "from_name": "Student",
            "subject": "Frage zur Klausur",
            "path": "/path/inbox.eml",
            "folder": "Inbox"
        },
        {
            "date": "2026-11-21T11:00:00",
            "from": "prof@th-koeln.de",
            "from_name": "Prof",
            "subject": "Antwort Klausur",
            "path": "/path/sent.eml",
            "folder": "SentItems"
        }
    ]

    mock_engine = MagicMock()
    mock_engine.search.return_value = mock_results

    with patch.object(GUITools, "engine", return_value=mock_engine):
        await app.perform_search()

        assert len(app.search_inbox_table.rows) == 1
        assert app.search_inbox_table.rows[0]["subject"] == "Frage zur Klausur"
        assert len(app.search_sent_table.rows) == 1
        assert app.search_sent_table.rows[0]["subject"] == "Antwort Klausur"
