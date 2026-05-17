from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from mcp_university.classifier.sort_emails import get_semester, extract_lastname, process_emails, write_report

def test_get_semester():
    # SoSe: 01.04. - 30.09.
    assert get_semester(datetime(2025, 4, 1)) == "2025_SoSe"
    assert get_semester(datetime(2025, 9, 30)) == "2025_SoSe"

    # WS: 01.10. - 31.03.
    assert get_semester(datetime(2025, 10, 1)) == "2025_26_WS"
    assert get_semester(datetime(2026, 3, 31)) == "2025_26_WS"
    assert get_semester(datetime(2025, 1, 15)) == "2024_25_WS"

def test_extract_lastname():
    assert extract_lastname("Max Mustermann") == "Mustermann"
    assert extract_lastname("Mustermann, Max") == "Mustermann"
    assert extract_lastname("Max Mustermann <max@example.com>") == "Mustermann"
    assert extract_lastname("Mustermann, Max <max@example.com>") == "Mustermann"
    assert extract_lastname("(No Sender)") == "Unknown"
    assert extract_lastname("") == "Unknown"

@patch('mcp_university.classifier.sort_emails.EmailClassifier')
@patch('mcp_university.classifier.sort_emails.MailParser')
@patch('extract_msg.openMsg')
def test_process_emails(mock_open_msg, mock_mail_parser, mock_classifier_class, tmp_path):
    # Setup source directory
    source_root = tmp_path / "source"
    inbox = source_root / "Inbox"
    sent = source_root / "Sent Items"
    inbox.mkdir(parents=True)
    sent.mkdir(parents=True)

    msg1 = inbox / "mail1.msg"
    msg1.touch()
    msg2 = sent / "mail2.msg"
    msg2.touch()

    # Setup target directory
    target_root = tmp_path / "target"
    target_root.mkdir()

    # Mock classifier
    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.side_effect = [
        {"prediction": "BachelorThesis"},
        {"prediction": "BachelorThesis"}
    ]

    # Mock parser
    mock_parser = mock_mail_parser.return_value
    mock_parser.get_email_date.side_effect = [
        datetime(2025, 5, 10), # SoSe
        datetime(2025, 11, 20) # WS
    ]

    # Mock extract_msg
    mock_msg1 = MagicMock()
    mock_msg1.sender = "Max Mustermann"

    mock_msg2 = MagicMock()
    mock_recip = MagicMock()
    mock_recip.name = "Erika Musterfrau"
    mock_msg2.recipients = [mock_recip]

    mock_open_msg.return_value.__enter__.side_effect = [mock_msg1, mock_msg2]

    config = {
        "BachelorThesis": str(target_root)
    }

    moved = process_emails(source_root, Path("dummy_model"), config)

    assert len(moved) == 2

    # Verify first file (Inbox)
    # Target: target/2025_SoSe/Mustermann/Inbox/mail1.msg
    expected_path1 = target_root / "2025_SoSe" / "Mustermann" / "Inbox" / "mail1.msg"
    assert expected_path1.exists()
    assert not msg1.exists()

    # Verify second file (Sent Items)
    # Target: target/2025_26_WS/Musterfrau/Sent Items/mail2.msg
    expected_path2 = target_root / "2025_26_WS" / "Musterfrau" / "Sent Items" / "mail2.msg"
    assert expected_path2.exists()
    assert not msg2.exists()

def test_write_report(tmp_path):
    source_root = tmp_path
    moved_emails = [
        {
            "class": "BachelorThesis",
            "semester": "2025_SoSe",
            "lastname": "Mustermann",
            "folder": "Inbox",
            "path": "/path/to/mail1.msg"
        },
        {
            "class": "BachelorThesis",
            "semester": "2025_26_WS",
            "lastname": "Musterfrau",
            "folder": "Sent Items",
            "path": "/path/to/mail2.msg"
        }
    ]

    write_report(source_root, moved_emails)

    report_path = source_root / "sorted_emails.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "# Sortierte E-Mails" in content
    assert "## BachelorThesis" in content
    assert "Mustermann" in content
    assert "Musterfrau" in content
