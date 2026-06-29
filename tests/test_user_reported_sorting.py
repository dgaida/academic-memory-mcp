from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
import pytest

from email_classifier.sort_emails import process_emails, extract_lastname
from mcp_university.utils.semester import get_semester

@pytest.fixture
def mock_deps():
    """Mocks dependencies for process_emails."""
    with patch('email_classifier.sort_emails.EmailClassifier') as mock_classifier_class, \
         patch('email_classifier.sort_emails.MailParser') as mock_mail_parser, \
         patch('extract_msg.openMsg') as mock_open_msg, \
         patch('shutil.move') as mock_move, \
         patch('email_classifier.sort_emails.get_config') as mock_get_config, \
         patch('email_classifier.sort_emails.find_student_folder') as mock_find_folder:

        # Setup common mocks
        mock_config = MagicMock()
        mock_config.user.emails = ["user@th-koeln.de"]
        mock_get_config.return_value = mock_config

        mock_find_folder.return_value = None 

        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}

        mock_parser = mock_mail_parser.return_value
        # Default date
        mock_parser.get_email_date.return_value = datetime(2025, 1, 1)

        yield {
            "open_msg": mock_open_msg,
            "config": mock_config,
            "move": mock_move,
            "parser": mock_parser
        }

def create_recipient(email, name, r_type):
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

def test_extract_lastname_cases():
    """Verifies extract_lastname logic for all reported cases."""
    # Case 1: Daniel Hans Anders <daniel_hans.anders@smail.th-koeln.de>
    assert extract_lastname("Daniel Hans Anders <daniel_hans.anders@smail.th-koeln.de>") == "Anders"
    assert extract_lastname("Daniel Hans Anders <daniel.hans.anders@smail.th-koeln.de>") == "Anders"
    
    # Case 2/3: Noe Abel Ida Kath <noe_abel_ida.kath@smail.th-koeln.de>
    assert extract_lastname("Noe Abel Ida Kath <noe_abel_ida.kath@smail.th-koeln.de>") == "Kath"
    
    # Case 4: Transactions of the Institute of Measurement and Control <onbehalfof@manuscriptcentral.com>
    assert extract_lastname("Transactions of the Institute of Measurement and Control <onbehalfof@manuscriptcentral.com>") == "Control"
    
    # Case 5/6: Phil Sans | Tanz GmbH <phil.sans@tanz-gmbh.com>
    assert extract_lastname("Phil Sans | Tanz GmbH <phil.sans@tanz-gmbh.com>") == "Sans"
    
    # Case 7: Dampf, Hans <dampf@fh-aachen.de>
    assert extract_lastname("Dampf, Hans <dampf@fh-aachen.de>") == "Dampf"

def test_semester_cases():
    """Verifies get_semester logic for reported dates."""
    assert get_semester(datetime(2026, 6, 6)) == "2026_SoSe"
    assert get_semester(datetime(2025, 11, 6)) == "2025_26_WS"
    assert get_semester(datetime(2025, 8, 6)) == "2025_SoSe"
    assert get_semester(datetime(2025, 8, 31)) == "2025_SoSe"

def test_full_sorting_case_3_cc(mock_deps, tmp_path):
    """3) Mail von 'Kath' an Nutzer (in CC). Sollte im Ordner 'Kath/Inbox' landen."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail_cc.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "Noe Abel Ida Kath <noe_abel_ida.kath@smail.th-koeln.de>"
    
    rec1 = create_recipient("other@th-koeln.de", "Other", 1) # TO
    rec2 = create_recipient("user@th-koeln.de", "User", 2) # CC (The tool user)
    mock_msg.recipients = [rec1, rec2]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    mock_deps["parser"].get_email_date.return_value = datetime(2025, 11, 6)

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert len(moved) == 1
    assert moved[0]["lastname"] == "Kath"
    assert moved[0]["semester"] == "2025_26_WS"
    assert moved[0]["folder"] == "Inbox"
    assert "2025_26_WS/Kath/Inbox" in moved[0]["path"].replace("\\", "/")

def test_full_sorting_case_6_cc(mock_deps, tmp_path):
    """6) Mail von 'Sans' an Nutzer (in CC). Sollte im Ordner 'Sans/Inbox' landen."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail_cc_sans.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "Phil Sans | Tanz GmbH <phil.sans@tanz-gmbh.com>"
    
    rec1 = create_recipient("other@th-koeln.de", "Other", 1) # TO
    rec2 = create_recipient("user@th-koeln.de", "User", 2) # CC
    mock_msg.recipients = [rec1, rec2]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    mock_deps["parser"].get_email_date.return_value = datetime(2025, 8, 6)

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert len(moved) == 1
    assert moved[0]["lastname"] == "Sans"
    assert moved[0]["semester"] == "2025_SoSe"
    assert moved[0]["folder"] == "Inbox"
    assert "2025_SoSe/Sans/Inbox" in moved[0]["path"].replace("\\", "/")

def test_full_sorting_case_4_control(mock_deps, tmp_path):
    """4) Mail von 'Control' an Nutzer. Sollte im Ordner 'Control/Inbox' landen."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail_control.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "Transactions of the Institute of Measurement and Control <onbehalfof@manuscriptcentral.com>"
    mock_msg.recipients = [create_recipient("user@th-koeln.de", "User", 1)]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg
    mock_deps["parser"].get_email_date.return_value = datetime(2025, 1, 1)

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["lastname"] == "Control"
    assert "Control/Inbox" in moved[0]["path"].replace("\\", "/")
