# ruff: noqa: E402
"""Tests for test_sort_emails.py."""
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies
mock_modules = [
    'torch',
    'torch.nn',
    'transformers',
    'sentence_transformers',
    'xgboost',
    'gradio',
    'qdrant_client',
    'docling',
    'liteparse',
    'sklearn.metrics.pairwise'
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

class MockTensor:
    pass
sys.modules['torch'].Tensor = MockTensor

from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from email_classifier.sort_emails import get_semester, extract_lastname, process_emails, write_report

def test_get_semester():
    """Test function docstring."""
    # SoSe: 01.04. - 30.09.
    assert get_semester(datetime(2025, 4, 1)) == "2025_SoSe"
    assert get_semester(datetime(2025, 9, 30)) == "2025_SoSe"

    # WS: 01.10. - 31.03.
    assert get_semester(datetime(2025, 10, 1)) == "2025_26_WS"
    assert get_semester(datetime(2026, 3, 31)) == "2025_26_WS"
    assert get_semester(datetime(2025, 1, 15)) == "2024_25_WS"

def test_extract_lastname():
    """Test function docstring."""
    assert extract_lastname("Max Mustermann") == "Mustermann"
    assert extract_lastname("Mustermann, Max") == "Mustermann"
    assert extract_lastname("Max Mustermann <mustermann@example.com>") == "Mustermann"
    assert extract_lastname("Mustermann Max <mustermann@example.com>") == "Mustermann"
    assert extract_lastname("Mustermann, Max <mustermann@example.com>") == "Mustermann"
    # Note: Logic was changed to preserve umlauts from display names
    assert extract_lastname("'Hans Müller'") == "Müller"
    assert extract_lastname("'Müller, Hans'") == "Müller"
    assert extract_lastname("(No Sender)") == "Unknown"
    assert extract_lastname("") == "Unknown"

@patch('email_classifier.sort_emails.EmailClassifier')
@patch('email_classifier.sort_emails.MailParser')
@patch('extract_msg.openMsg')
def test_process_emails(mock_open_msg, mock_mail_parser, mock_classifier_class, tmp_path):
    """Test function docstring."""
    # Setup source directory
    source_root = tmp_path / "source"
    some_folder = source_root / "ArbitraryFolder"
    some_folder.mkdir(parents=True)

    # Use names that sort predictably: a_mail1.msg, b_mail2.msg, c_mail3.msg
    msg1 = some_folder / "a_mail1.msg"
    msg1.touch()
    msg2 = some_folder / "b_mail2.msg"
    msg2.touch()

    # Subdirectory test
    sub_folder = some_folder / "Deep" / "Subfolder"
    sub_folder.mkdir(parents=True)
    msg3 = sub_folder / "c_mail3.msg"
    msg3.touch()

    # Setup target directory
    target_root = tmp_path / "target"
    target_root.mkdir()

    # Mock classifier
    mock_classifier = mock_classifier_class.return_value
    mock_classifier.predict.side_effect = [
        {"prediction": "BachelorThesis"}, # a_mail1
        {"prediction": "BachelorThesis"}, # b_mail2
        {"prediction": "BachelorThesis"}  # c_mail3
    ]

    # Mock parser
    mock_parser = mock_mail_parser.return_value
    mock_parser.get_email_date.side_effect = [
        datetime(2025, 5, 10), # a_mail1 SoSe
        datetime(2025, 11, 20), # b_mail2 WS
        datetime(2025, 6, 10)  # c_mail3 SoSe
    ]

    # Mock extract_msg
    mock_msg1 = MagicMock()
    mock_msg1.sender = "max.mustermann@smail.th-koeln.de"
    mock_msg1.recipients = []

    mock_msg2 = MagicMock()
    mock_msg2.sender = "daniel.gaida@th-koeln.de"
    mock_recip2 = MagicMock()
    mock_recip2.email = "erika.musterfrau@smail.fh-koeln.de"
    mock_recip2.name = "Erika Musterfrau"
    mock_msg2.recipients = [mock_recip2]

    mock_msg3 = MagicMock()
    mock_msg3.sender = "hans.huber@smail.th-koeln.de"
    mock_recip3 = MagicMock()
    mock_recip3.email = "hans.huber@smail.th-koeln.de"
    mock_recip3.name = "Hans Huber"
    mock_msg3.recipients = [mock_recip3]

    # Correct mocking for context manager with multiple calls
    mock_open_msg.return_value.__enter__.side_effect = [mock_msg1, mock_msg2, mock_msg3]

    config = {
        "BachelorThesis": str(target_root)
    }

    # IMPORTANT: We MUST mock shutil.move to verify it's called correctly,
    # as the real shutil.move will fail if the file doesn't exist (which it won't after being moved once)

    with patch('shutil.move'):
        # Mock university user emails
        with patch('email_classifier.sort_emails.get_config') as mock_cfg:
            mock_cfg.return_value.user.emails = ["daniel.gaida@th-koeln.de"]
            moved = process_emails(source_root, Path("dummy_model"), config)

    assert len(moved) == 3

    # Check that moved list has correct entries
    assert moved[0]["lastname"] == "Mustermann"
    assert moved[1]["lastname"] == "Musterfrau"
    assert moved[2]["lastname"] == "Huber"

def test_write_report(tmp_path):
    """Test function docstring."""
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
    assert "/path/to/mail1.msg" in content
