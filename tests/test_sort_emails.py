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
    assert extract_lastname("'Hans Müller'") == "Müller"
    assert extract_lastname("'Müller, Hans'") == "'Müller"
    assert extract_lastname("(No Sender)") == "Unknown"
    assert extract_lastname("") == "Unknown"

@patch('mcp_university.classifier.sort_emails.EmailClassifier')
@patch('mcp_university.classifier.sort_emails.MailParser')
@patch('extract_msg.openMsg')
def test_process_emails(mock_open_msg, mock_mail_parser, mock_classifier_class, tmp_path):
    # Setup source directory - now with arbitrary structure
    source_root = tmp_path / "source"
    some_folder = source_root / "ArbitraryFolder"
    some_folder.mkdir(parents=True)

    msg1 = some_folder / "mail1.msg"
    msg1.touch()
    msg2 = some_folder / "mail2.msg"
    msg2.touch()

    # Subdirectory test
    sub_folder = some_folder / "Deep" / "Subfolder"
    sub_folder.mkdir(parents=True)
    msg3 = sub_folder / "mail3.msg"
    msg3.touch()

    # Setup target directory
    target_root = tmp_path / "target"
    target_root.mkdir()

    # Mock classifier
    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.side_effect = [
        {"prediction": "BachelorThesis"}, # mail1
        {"prediction": "BachelorThesis"}, # mail2
        {"prediction": "BachelorThesis"}  # mail3
    ]

    # Mock parser
    mock_parser = mock_mail_parser.return_value
    mock_parser.get_email_date.side_effect = [
        datetime(2025, 5, 10), # mail1 SoSe
        datetime(2025, 11, 20), # mail2 WS
        datetime(2025, 6, 10)  # mail3 SoSe
    ]

    # Mock extract_msg
    # Mail 1: From Student -> Inbox
    mock_msg1 = MagicMock()
    mock_msg1.sender = "max.mustermann@smail.th-koeln.de"
    mock_msg1.recipients = []

    # Mail 2: From Daniel Gaida to Student -> SentItems
    mock_msg2 = MagicMock()
    mock_msg2.sender = "daniel.gaida@th-koeln.de"
    mock_recip2 = MagicMock()
    mock_recip2.email = "erika.musterfrau@smail.fh-koeln.de"
    mock_recip2.name = "Erika Musterfrau"
    mock_msg2.recipients = [mock_recip2]

    # Mail 3: From Unknown to Student -> SentItems (fallback logic)
    mock_msg3 = MagicMock()
    mock_msg3.sender = "someone@else.com"
    mock_recip3 = MagicMock()
    mock_recip3.email = "hans.huber@smail.th-koeln.de"
    mock_recip3.name = "Hans Huber"
    mock_msg3.recipients = [mock_recip3]

    mock_open_msg.return_value.__enter__.side_effect = [mock_msg1, mock_msg2, mock_msg3]

    config = {
        "BachelorThesis": str(target_root)
    }

    moved = process_emails(source_root, Path("dummy_model"), config)

    assert len(moved) == 3

    # Verify first file (From Student)
    expected_path1 = target_root / "2025_SoSe" / "Mustermann" / "Inbox" / "mail1.msg"
    assert expected_path1.exists()

    # Verify second file (From Gaida to Student)
    expected_path2 = target_root / "2025_26_WS" / "Musterfrau" / "SentItems" / "mail2.msg"
    assert expected_path2.exists()

    # Verify third file (From Unknown to Student)
    expected_path3 = target_root / "2025_SoSe" / "Huber" / "SentItems" / "mail3.msg"
    assert expected_path3.exists()

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
            "folder": "SentItems",
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
