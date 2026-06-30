"""Tests für die neuen Anforderungen an die E-Mail-Sortierung."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from email_classifier.scripts.sort_emails import extract_lastname, process_emails
from scripts.fix_email_folders import fix_folders

def test_requirement_1_greedy_match():
    """Anforderung 1: Greedy multi-word surname matching.
    'A B C D <a_b.c_d@smail.th-koeln.de>' -> 'C D'
    """
    input_str = "A B C D <a_b.c_d@smail.th-koeln.de>"
    assert extract_lastname(input_str) == "C D"

def test_requirement_2_dot_extraction():
    """Anforderung 2: Dot-segment extraction.
    'TH Köln <nils_karl.mode@smail.th-koeln.de>' -> 'Mode'
    """
    input_str = "TH Köln <nils_karl.mode@smail.th-koeln.de>"
    assert extract_lastname(input_str) == "Mode"

def test_requirement_3_dash_preservation():
    """Anforderung 3: Dash preservation for system addresses.
    'Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>' -> 'Praxissemester-Inf'
    """
    input_str = "Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>"
    assert extract_lastname(input_str) == "Praxissemester-Inf"

def test_requirement_4_validation_fallback():
    """Anforderung 4: Validation fallback.
    'Wester Helmut <HWester@tuev.com>' -> 'HWester' (since Helmut not in HWester)
    """
    input_str = "Wester Helmut <HWester@tuev.com>"
    assert extract_lastname(input_str) == "HWester"

@pytest.fixture
def mock_sort_deps():
    """Mockt Abhängigkeiten für E-Mail-Sortierung."""
    with patch('email_classifier.scripts.sort_emails.EmailClassifier') as mock_classifier_class,          patch('email_classifier.scripts.sort_emails.MailParser'),          patch('extract_msg.openMsg') as mock_open_msg,          patch('shutil.move') as mock_move,          patch('email_classifier.scripts.sort_emails.get_config') as mock_get_config,          patch('email_classifier.scripts.sort_emails.get_semester') as mock_get_semester,          patch('email_classifier.scripts.sort_emails.find_student_folder') as mock_find_folder:

        mock_config = MagicMock()
        mock_config.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_config
        mock_get_semester.return_value = "2024_SoSe"
        mock_find_folder.return_value = None
        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}
        
        yield {"open_msg": mock_open_msg, "move": mock_move, "config": mock_config}

def test_process_sorted_mails_logic(mock_sort_deps, tmp_path):
    """Prüft ob process_emails (genutzt von process_sorted_emails.py) die Anforderungen erfüllt."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "test.msg").touch()
    
    mock_msg = MagicMock()
    # Case 2: TH Köln <nils_karl.mode@smail.th-koeln.de>
    mock_msg.sender = "TH Köln <nils_karl.mode@smail.th-koeln.de>"
    mock_msg.recipients = []
    
    mock_sort_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    
    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)
    
    assert moved[0]["lastname"] == "Mode"

def test_fix_email_folders_logic(tmp_path):
    """Prüft ob fix_email_folders.py alle Anforderungen erfüllt."""
    base = tmp_path / "BachelorThesis"
    base.mkdir()
    
    # Setup test mails
    mail1 = base / "mail1.msg"
    mail1.touch()
    mail2 = base / "mail2.msg"
    mail2.touch()
    
    config_path = tmp_path / "config.yaml"
    import yaml
    with open(config_path, "w") as f:
        yaml.dump({"BachelorThesis": str(base)}, f)

    # Mock Details für MailParser
    mock_details_1 = {
        "date": "2024-05-01",
        "from_name": "A B C D",
        "from_email": "a_b.c_d@smail.th-koeln.de"
    }
    mock_details_2 = {
        "date": "2024-05-01",
        "from_name": "TH Köln",
        "from_email": "nils_karl.mode@smail.th-koeln.de"
    }
    
    with patch("scripts.fix_email_folders.MailParser") as mock_parser_class,          patch("scripts.fix_email_folders.get_config") as mock_get_config,          patch("scripts.fix_email_folders.get_semester") as mock_get_semester:
        
        mock_parser = mock_parser_class.return_value
        # Side effect to return different details
        mock_parser.get_email_details.side_effect = [mock_details_1, mock_details_2]
        
        mock_conf = MagicMock()
        mock_conf.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_conf
        mock_get_semester.return_value = "2024_SoSe"
        
        fix_folders(config_path, dry_run=False)
        
        # Check Requirement 1
        assert (base / "2024_SoSe" / "C D" / "Inbox" / "mail1.msg").exists()
        # Check Requirement 2
        assert (base / "2024_SoSe" / "Mode" / "Inbox" / "mail2.msg").exists()
