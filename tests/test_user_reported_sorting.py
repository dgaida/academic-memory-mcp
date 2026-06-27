"""Tests für vom Nutzer gemeldete Sortierfälle."""
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from typing import Any, List, Optional
import pytest

from mcp_university.classifier.sort_emails import process_emails, extract_lastname
from mcp_university.utils.semester import get_semester

@pytest.fixture
def mock_deps() -> Any:
    """Mockt Abhängigkeiten."""
    with patch('mcp_university.classifier.sort_emails.EmailClassifier') as mock_classifier_class,          patch('mcp_university.classifier.sort_emails.MailParser') as mock_mail_parser,          patch('extract_msg.openMsg') as mock_open_msg,          patch('shutil.move') as mock_move,          patch('mcp_university.classifier.sort_emails.get_config') as mock_get_config,          patch('mcp_university.classifier.sort_emails.find_student_folder') as mock_find_folder:

        mock_config = MagicMock()
        mock_config.user.emails = ["user@th-koeln.de"]
        mock_get_config.return_value = mock_config
        mock_find_folder.return_value = None 
        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}
        mock_parser = mock_mail_parser.return_value
        mock_parser.get_email_date.return_value = datetime(2025, 1, 1)

        yield {"open_msg": mock_open_msg, "config": mock_config, "move": mock_move, "parser": mock_parser}

def create_recipient(email: str, name: str, r_type: int) -> MagicMock:
    """Mock Empfänger."""
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

def test_extract_lastname_cases() -> None:
    """Verifiziert die Nachnamen-Extraktion."""
    assert extract_lastname("Daniel Hans Anders <daniel_hans.anders@smail.th-koeln.de>") == "Anders"
    assert extract_lastname("Noe Abel Ida Kath <noe_abel_ida.kath@smail.th-koeln.de>") == "Kath"
    # Case with long name and generic local part
    assert extract_lastname("Transactions of the Institute of Measurement and Control <onbehalfof@manuscriptcentral.com>") == "Control"
    assert extract_lastname("Phil Sans | Tanz GmbH <phil.sans@tanz-gmbh.com>") == "Sans"
    assert extract_lastname("Dampf, Hans <dampf@fh-aachen.de>") == "Dampf"

def test_semester_cases() -> None:
    """Verifiziert Semester-Logik."""
    assert get_semester(datetime(2026, 6, 6)) == "2026_SoSe"
    assert get_semester(datetime(2025, 11, 6)) == "2025_26_WS"

def test_full_sorting_case_3_cc(mock_deps: Any, tmp_path: Path) -> None:
    """Test Case 3 CC."""
    source_root = tmp_path / "source"; source_root.mkdir(); (source_root / "mail_cc.msg").touch()
    mock_msg = MagicMock(); mock_msg.sender = "Noe Abel Ida Kath <noe_abel_ida.kath@smail.th-koeln.de>"
    rec1 = create_recipient("other@th-koeln.de", "Other", 1)
    rec2 = create_recipient("user@th-koeln.de", "User", 2)
    mock_msg.recipients = [rec1, rec2]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "Kath"

def test_full_sorting_case_6_cc(mock_deps: Any, tmp_path: Path) -> None:
    """Test Case 6 CC."""
    source_root = tmp_path / "source"; source_root.mkdir(); (source_root / "mail_cc_sans.msg").touch()
    mock_msg = MagicMock(); mock_msg.sender = "Phil Sans | Tanz GmbH <phil.sans@tanz-gmbh.com>"
    rec1 = create_recipient("other@th-koeln.de", "Other", 1); rec2 = create_recipient("user@th-koeln.de", "User", 2)
    mock_msg.recipients = [rec1, rec2]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "Sans"

def test_full_sorting_case_4_control(mock_deps: Any, tmp_path: Path) -> None:
    """Test Case 4 Control."""
    source_root = tmp_path / "source"; source_root.mkdir(); (source_root / "mail_control.msg").touch()
    mock_msg = MagicMock(); mock_msg.sender = "Transactions of the Institute of Measurement and Control <onbehalfof@manuscriptcentral.com>"
    mock_msg.recipients = [create_recipient("user@th-koeln.de", "User", 1)]
    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)
    assert moved[0]["lastname"] == "Control"
