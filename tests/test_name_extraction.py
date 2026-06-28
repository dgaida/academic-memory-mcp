"""Tests für die Namensextraktion und das Sortieren von E-Mails."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from typing import Any
from mcp_university.classifier.sort_emails import extract_firstname, extract_lastname, process_emails

@pytest.mark.parametrize("input_str, expected_first, expected_last", [
    ("max.muster@smail.th-koeln.de", "Max", "Muster"),
    ("max_hans.muster@smail.th-koeln.de", "Max Hans", "Muster"),
    ("max.muster_hase@smail.th-koeln.de", "Max", "Muster Hase"),
    ("max.muster-hase@smail.th-koeln.de", "Max", "Muster-Hase"),
    ("hans-peter.muster-hase@smail.th-koeln.de", "Hans-Peter", "Muster-Hase"),
    ("max_hans.muster_hase@smail.th-koeln.de", "Max Hans", "Muster Hase"),
    ("Angela Spaß (aspass) <angela.spass@smail.th-koeln.de>", "Angela", "Spaß"),
    ("studium-gm@th-koeln.de", "Unknown", "Studium-Gm"),
    ("f10-request@f10.th-koeln.de; im Auftrag von; Marcel Mueller, B.Sc. <marcel.mueller@th-koeln.de>", "Marcel", "Mueller"),
    ("Sabrina Tuba <stuba@fft.com>", "Sabrina", "Tuba"),
    ("stuba@fft.com", "Unknown", "Stuba"),
])
def test_name_extraction(input_str: str, expected_first: str, expected_last: str) -> None:
    """Testet die Extraktion von Vor- und Nachnamen aus verschiedenen Formaten.

    Args:
        input_str: Der Eingabestring (Name/Email).
        expected_first: Erwarteter Vorname.
        expected_last: Erwarteter Nachname.
    """
    first = extract_firstname(input_str)
    last = extract_lastname(input_str)

    assert first == expected_first, f"First name mismatch for {input_str}: expected {expected_first}, got {first}"
    assert last == expected_last, f"Last name mismatch for {input_str}: expected {expected_last}, got {last}"

@pytest.fixture
def mock_deps() -> Any:
    """Mockt Abhängigkeiten für die Sortier-Tests.

    Yields:
        Dictionary mit Mock-Objekten.
    """
    with patch('mcp_university.classifier.sort_emails.EmailClassifier') as mock_classifier_class,          patch('mcp_university.classifier.sort_emails.MailParser') as mock_mail_parser,          patch('extract_msg.openMsg') as mock_open_msg,          patch('shutil.move') as mock_move,          patch('mcp_university.classifier.sort_emails.get_config') as mock_get_config,          patch('mcp_university.classifier.sort_emails.get_semester') as mock_get_semester,          patch('mcp_university.classifier.sort_emails.find_student_folder') as mock_find_folder:

        mock_config = MagicMock()
        mock_config.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_config

        mock_get_semester.return_value = "2024_25_WS"
        mock_find_folder.return_value = None

        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}

        mock_parser = mock_mail_parser.return_value
        mock_parser.get_email_date.return_value = datetime(2024, 10, 1)

        yield {
            "open_msg": mock_open_msg,
            "config": mock_config,
            "move": mock_move,
            "find_folder": mock_find_folder,
            "classifier": mock_classifier
        }

def create_rec(email: str, name: str, r_type: int) -> MagicMock:
    """Erstellt ein Mock-Recipient-Objekt.

    Args:
        email: E-Mail-Adresse.
        name: Anzeigename.
        r_type: Typ (1=TO, 2=CC).

    Returns:
        MagicMock: Gemockter Empfänger.
    """
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

@pytest.mark.parametrize("sender_str, expected_lastname", [
    ("max.muster@smail.th-koeln.de", "Muster"),
    ("max_hans.muster@smail.th-koeln.de", "Muster"),
    ("max.muster_hase@smail.th-koeln.de", "Muster Hase"),
    ("max.muster-hase@smail.th-koeln.de", "Muster-Hase"),
    ("hans-peter.muster-hase@smail.th-koeln.de", "Muster-Hase"),
    ("max_hans.muster_hase@smail.th-koeln.de", "Muster Hase"),
    ("Angela Spaß (aspass) <angela.spass@smail.th-koeln.de>", "Spaß"),
    ("studium-gm@th-koeln.de", "Studium-Gm"),
    ("f10-request@f10.th-koeln.de; im Auftrag von; Marcel Mueller, B.Sc. <marcel.mueller@th-koeln.de>", "Mueller"),
    ("Sabrina Tuba <stuba@fft.com>", "Tuba"),
    ("stuba@fft.com", "Stuba"),
])
def test_sorting_inbox(mock_deps: Any, tmp_path: Path, sender_str: str, expected_lastname: str) -> None:
    """Testet das Sortieren einer eingehenden E-Mail in die Inbox.

    Args:
        mock_deps: Gemockte Abhängigkeiten.
        tmp_path: Temporärer Pfad.
        sender_str: Sender-String.
        expected_lastname: Erwarteter Nachname für den Ordner.
    """
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "test.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = sender_str
    mock_msg.recipients = [create_rec("daniel.gaida@th-koeln.de", "Daniel Gaida", 1)]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert len(moved) == 1
    assert moved[0]["folder"] == "Inbox"
    assert moved[0]["lastname"] == expected_lastname

    # Check that the path contains the expected lastname
    expected_path = Path(tmp_path / "target" / "2024_25_WS" / expected_lastname / "Inbox" / "test.msg")
    assert Path(moved[0]["path"]) == expected_path
