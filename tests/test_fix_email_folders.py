"""Tests for the fix_email_folders script."""
import pytest
import yaml
import shutil
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
from scripts.fix_email_folders import fix_folders, walk_bottom_up

@pytest.fixture
def mock_config_path(tmp_path):
    """Fixture for creating a mock config file.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path: Path to the created config file.
    """
    config = {
        "class_paths": {
            "test_class": str(tmp_path / "emails")
        }
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file

@pytest.fixture
def setup_emails(tmp_path):
    """Fixture for setting up a mock email directory structure.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path: Path to the created emails directory.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)

    # Email in root (should be moved)
    email1 = base_path / "20231027_100000.msg"
    email1.write_text("dummy content")

    # Email in "correct" dir
    correct_dir = base_path / "2023_24_WS" / "Doe" / "Inbox"
    correct_dir.mkdir(parents=True, exist_ok=True)
    email2 = correct_dir / "20231028_100000.msg"
    email2.write_text("dummy content")

    return base_path

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
@patch("scripts.fix_email_folders.shutil.move")
@patch("scripts.fix_email_folders.get_semester")
@patch("scripts.fix_email_folders.extract_lastname")
def test_fix_folders_basic(mock_extract, mock_semester, mock_move, mock_get_config, mock_parser_class, mock_config_path, setup_emails):
    """Tests basic folder fixing functionality.

    Args:
        mock_extract: Mock for extract_lastname.
        mock_semester: Mock for get_semester.
        mock_move: Mock for shutil.move.
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        setup_emails: Email setup fixture.
    """
    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "John Doe"
    }
    mock_semester.return_value = "2023_24_WS"
    mock_extract.return_value = "Doe"
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    fix_folders(mock_config_path, dry_run=False, full_verify=False)

    mock_move.assert_called()

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
@patch("scripts.fix_email_folders.shutil.move")
def test_fix_folders_dry_run(mock_move, mock_get_config, mock_parser_class, mock_config_path, setup_emails):
    """Tests dry-run mode.

    Args:
        mock_move: Mock for shutil.move.
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        setup_emails: Email setup fixture.
    """
    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "John Doe"
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    fix_folders(mock_config_path, dry_run=True, full_verify=False)

    mock_move.assert_not_called()

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
@patch("scripts.fix_email_folders.shutil.move")
@patch("scripts.fix_email_folders.get_semester")
@patch("scripts.fix_email_folders.extract_lastname")
@patch("scripts.fix_email_folders.find_student_folder")
def test_fix_folders_full_verify(mock_find, mock_extract, mock_semester, mock_move, mock_get_config, mock_parser_class, mock_config_path, setup_emails):
    """Tests full-verify mode.

    Args:
        mock_find: Mock for find_student_folder.
        mock_extract: Mock for extract_lastname.
        mock_semester: Mock for get_semester.
        mock_move: Mock for shutil.move.
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        setup_emails: Email setup fixture.
    """
    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "John Doe",
        "to": [],
        "cc": []
    }
    mock_find.return_value = None
    mock_semester.side_effect = ["2023_24_WS", "2024_SS"]
    mock_extract.return_value = "Doe"
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    fix_folders(mock_config_path, dry_run=False, full_verify=True)
    assert mock_move.call_count >= 2

def test_walk_bottom_up(tmp_path):
    """Tests walk_bottom_up helper.

    Args:
        tmp_path: Pytest temporary path fixture.
    """
    d1 = tmp_path / "a"
    d1.mkdir()
    d2 = d1 / "b"
    d2.mkdir()
    f = d2 / "file.txt"
    f.write_text("hi")

    results = list(walk_bottom_up(tmp_path))
    paths = [Path(r[0]) for r in results]
    assert d2 in paths
    assert d1 in paths
    assert paths.index(d2) < paths.index(d1)

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_sent_items(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests classification of SentItems.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "prof@th-koeln.de",
        "from_name": "Prof",
        "to": [{"name": "Student", "email": "student@smail.th-koeln.de"}],
        "cc": []
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        args, _ = mock_move.call_args
        assert "SentItems" in str(args[1])

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_associated_files(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests moving of associated .md and .txt files.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")
    assoc_file = base_path / "20231027_100000.md"
    assoc_file.write_text("summary")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "Student"
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        assert mock_move.call_count == 2 # Email + MD file

def test_fix_folders_no_config(tmp_path):
    """Tests behavior when config file is missing.

    Args:
        tmp_path: Pytest temporary path fixture.
    """
    fix_folders(tmp_path / "nonexistent.yaml")

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
@patch("scripts.fix_email_folders.find_student_folder")
@patch("scripts.fix_email_folders.extract_lastname")
def test_fix_folders_to_recipient_loop(mock_extract, mock_find, mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests lastname extraction from recipient loop.

    Args:
        mock_extract: Mock for extract_lastname.
        mock_find: Mock for find_student_folder.
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")
    mock_find.return_value = None

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "prof@th-koeln.de",
        "to": [{"name": "Student", "email": "student@smail.th-koeln.de"}],
        "cc": []
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]
    mock_extract.return_value = "Student"

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        args, _ = mock_move.call_args
        assert "Student" in str(args[1])

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_fallback_inbox(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests fallback to Inbox when user sends to non-student.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "Student",
        "to": [{"name": "Prof", "email": "prof@th-koeln.de"}],
        "cc": []
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        args, _ = mock_move.call_args
        assert "Inbox" in str(args[1])

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_cleanup_empty_dirs(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests removal of empty directories.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    empty_dir = base_path / "Empty"
    empty_dir.mkdir()

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = None # Skip processing files

    fix_folders(mock_config_path, dry_run=False, full_verify=False)
    assert not empty_dir.exists()

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_existing_dest(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests that existing destination files are not overwritten.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")

    dest_dir = base_path / "2023_24_WS" / "Student" / "Inbox"
    dest_dir.mkdir(parents=True)
    existing_dest = dest_dir / "20231027_100000.msg"
    existing_dest.write_text("already here")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "Student"
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        mock_move.assert_not_called()

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
def test_fix_folders_external_sender_to_sent_items(mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests folder assignment for external senders.

    Args:
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "someone@external.com",
        "from_name": "External",
        "to": [{"name": "Student", "email": "student@smail.th-koeln.de"}],
        "cc": []
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        args, _ = mock_move.call_args
        assert "SentItems" in str(args[1])

@patch("scripts.fix_email_folders.MailParser")
@patch("scripts.fix_email_folders.get_config")
@patch("scripts.fix_email_folders.extract_lastname")
def test_fix_folders_sender_is_student(mock_extract, mock_get_config, mock_parser_class, mock_config_path, tmp_path):
    """Tests folder assignment when sender is a student.

    Args:
        mock_extract: Mock for extract_lastname.
        mock_get_config: Mock for get_config.
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    base_path = tmp_path / "emails"
    base_path.mkdir(exist_ok=True)
    email_file = base_path / "20231027_100000.msg"
    email_file.write_text("dummy")

    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {
        "date": datetime(2023, 10, 27),
        "from_email": "student@smail.th-koeln.de",
        "from_name": "Student"
    }
    mock_get_config.return_value.user.emails = ["prof@th-koeln.de"]
    mock_extract.return_value = "Student"

    with patch("scripts.fix_email_folders.shutil.move") as mock_move:
        fix_folders(mock_config_path, dry_run=False, full_verify=False)
        args, _ = mock_move.call_args
        assert "Inbox" in str(args[1])
        assert "Student" in str(args[1])

@patch("scripts.fix_email_folders.MailParser")
def test_fix_folders_no_date(mock_parser_class, mock_config_path, setup_emails):
    """Tests behavior when email date is missing.

    Args:
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        setup_emails: Email setup fixture.
    """
    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.return_value = {"date": None}

    # Should skip
    fix_folders(mock_config_path, dry_run=False, full_verify=False)

def test_fix_folders_missing_base_path(mock_config_path, tmp_path):
    """Tests behavior when base path is missing.

    Args:
        mock_config_path: Mock config path.
        tmp_path: Pytest temporary path fixture.
    """
    # Base path does not exist
    config = {"class_paths": {"test": str(tmp_path / "nonexistent")}}
    with open(mock_config_path, "w") as f:
        yaml.dump(config, f)
    fix_folders(mock_config_path)

@patch("scripts.fix_email_folders.MailParser")
def test_fix_folders_exception(mock_parser_class, mock_config_path, setup_emails):
    """Tests exception handling during processing.

    Args:
        mock_parser_class: Mock for MailParser.
        mock_config_path: Mock config path.
        setup_emails: Email setup fixture.
    """
    mock_parser = mock_parser_class.return_value
    mock_parser.get_email_details.side_effect = Exception("error")

    # Should catch and continue
    fix_folders(mock_config_path)
