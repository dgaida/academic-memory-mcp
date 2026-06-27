"""Tests für neue Sortieranforderungen."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import Any

from mcp_university.classifier.sort_emails import extract_lastname, process_emails
import scripts.fix_email_folders as fix_email_folders

def create_recipient(email: str, name: str, r_type: int) -> MagicMock:
    """Erstellt ein Mock-Recipient-Objekt."""
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

@pytest.fixture
def mock_deps() -> Any:
    """Mockt Abhängigkeiten für Tests."""
    with patch('mcp_university.classifier.sort_emails.EmailClassifier') as mock_classifier_class,          patch('mcp_university.classifier.sort_emails.MailParser') as mock_mail_parser,          patch('extract_msg.openMsg') as mock_open_msg,          patch('shutil.move') as mock_move,          patch('mcp_university.classifier.sort_emails.get_config') as mock_get_config,          patch('mcp_university.classifier.sort_emails.get_semester') as mock_get_semester,          patch('mcp_university.classifier.sort_emails.find_student_folder') as mock_find_folder:

        mock_config = MagicMock()
        mock_config.user.emails = ["user@th-koeln.de"]
        mock_get_config.return_value = mock_config
        mock_get_semester.return_value = "2024_25_WS"
        mock_find_folder.return_value = None
        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}
        mock_parser = mock_mail_parser.return_value
        mock_parser.get_email_date.return_value = datetime(2024, 10, 1)

        yield {
            "open_msg": mock_open_msg,
            "move": mock_move,
            "config": mock_config,
            "parser": mock_parser
        }

def test_extract_lastname_new_cases() -> None:
    """Testet die Extraktion für die neuen Requirement-Fälle."""
    assert extract_lastname("A B C D <a_b.c_d@smail.th-koeln.de>") == "C D"
    assert extract_lastname("TH Köln <nils_karl.mode@smail.th-koeln.de>") == "Mode"
    assert extract_lastname("Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>") == "Praxissemester-Inf"
    assert extract_lastname("Wester Helmut <HWester@tuev.com>") == "HWester"

def test_fix_email_folders_integration(tmp_path: Path) -> None:
    """Integrationstest für fix_email_folders.py."""
    base_dir = tmp_path / "BachelorThesis"
    base_dir.mkdir()
    mail_file = base_dir / "20241001_100000.msg"
    mail_file.write_text("dummy content")

    config_file = tmp_path / "config.yaml"
    import yaml
    with open(config_file, "w") as f:
        yaml.dump({"class_paths": {"BachelorThesis": str(base_dir)}}, f)

    with patch('scripts.fix_email_folders.MailParser') as mock_parser_class,          patch('scripts.fix_email_folders.get_config') as mock_get_config:

        mock_parser = mock_parser_class.return_value
        mock_parser.get_email_details.return_value = {
            "date": datetime(2024, 10, 1),
            "from_email": "a_b.c_d@smail.th-koeln.de",
            "from_name": "A B C D",
            "to": [],
            "cc": []
        }

        mock_config = MagicMock()
        mock_config.user.emails = ["user@th-koeln.de"]
        mock_get_config.return_value = mock_config

        with patch('scripts.fix_email_folders.find_student_folder', return_value=None):
             fix_email_folders.fix_folders(config_file, dry_run=False, full_verify=False)

    from mcp_university.utils.semester import get_semester
    semester = get_semester(datetime(2024, 10, 1))
    expected_path = base_dir / semester / "C D" / "Inbox" / "20241001_100000.msg"
    assert expected_path.exists()

def test_process_sorted_mails_case_2(mock_deps: Any, tmp_path: Path) -> None:
    """Nils Karl Mode Fall."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mode.msg").touch()
    mock_msg = MagicMock()
    mock_msg.sender = "TH Köln <nils_karl.mode@smail.th-koeln.de>"
    mock_msg.sender_email = "nils_karl.mode@smail.th-koeln.de"
    mock_msg.recipients = [create_recipient("user@th-koeln.de", "User", 1)]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    target_root = tmp_path / "target"
    config = {"BachelorThesis": str(target_root)}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "Mode"

def test_requirement_3_praxissemester(mock_deps: Any, tmp_path: Path) -> None:
    """Praxissemester Fall."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "praxis.msg").touch()
    mock_msg = MagicMock()
    mock_msg.sender = "Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>"
    mock_msg.sender_email = "praxissemester-inf@f10.th-koeln.de"
    mock_msg.recipients = [create_recipient("user@th-koeln.de", "User", 1)]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    target_root = tmp_path / "target"
    config = {"BachelorThesis": str(target_root)}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "Praxissemester-Inf"

def test_requirement_4_wester_helmut(mock_deps: Any, tmp_path: Path) -> None:
    """Wester Helmut Fall."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "wester.msg").touch()
    mock_msg = MagicMock()
    mock_msg.sender = "Wester Helmut <HWester@tuev.com>"
    mock_msg.sender_email = "HWester@tuev.com"
    mock_msg.recipients = [create_recipient("user@th-koeln.de", "User", 1)]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    target_root = tmp_path / "target"
    config = {"BachelorThesis": str(target_root)}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "HWester"
