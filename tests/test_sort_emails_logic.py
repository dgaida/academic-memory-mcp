import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
import pytest

# Stub dependencies to avoid torch error
sys.modules['mcp_university.classifier.engine'] = MagicMock()
sys.modules['mcp_university.parser.mail_parser'] = MagicMock()
sys.modules['torch'] = MagicMock()

# Import after stubbing
from mcp_university.classifier.sort_emails import process_emails # noqa: E402

@pytest.fixture
def mock_dependencies():
    with patch('mcp_university.classifier.sort_emails.EmailClassifier') as mock_classifier_class, \
         patch('mcp_university.classifier.sort_emails.MailParser') as mock_mail_parser, \
         patch('extract_msg.openMsg') as mock_open_msg, \
         patch('shutil.move') as mock_move, \
         patch('mcp_university.classifier.sort_emails.get_config') as mock_get_config, \
         patch('mcp_university.classifier.sort_emails.get_semester') as mock_get_semester, \
         patch('mcp_university.classifier.sort_emails.find_student_folder') as mock_find_folder:

        # Setup common mocks
        mock_config = MagicMock()
        mock_config.user.emails = ["daniel.gaida@th-koeln.de"]
        mock_get_config.return_value = mock_config

        mock_get_semester.return_value = "2024_25_WS"
        mock_find_folder.return_value = None # Force new folder creation

        mock_classifier = mock_classifier_class.return_value
        mock_classifier.predict.return_value = {"prediction": "BachelorThesis"}

        mock_parser = mock_mail_parser.return_value
        mock_parser.get_email_date.return_value = datetime(2024, 10, 1)

        yield {
            "open_msg": mock_open_msg,
            "config": mock_config,
            "move": mock_move
        }

def create_recipient(email, name, r_type):
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

def test_sent_items_multiple_to(mock_dependencies, tmp_path):
    """Test: User sends to multiple students. Should take the first 'To' student."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail1.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"

    rec1 = create_recipient("mustermann@smail.th-koeln.de", "Max Mustermann", 1) # TO
    rec2 = create_recipient("musterfrau@smail.th-koeln.de", "Erika Musterfrau", 1) # TO
    mock_msg.recipients = [rec1, rec2]

    # Mocking context manager
    mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "SentItems"
    assert moved[0]["lastname"] == "Mustermann"

def test_sent_items_to_and_cc(mock_dependencies, tmp_path):
    """Test: User sends to Student (TO) and Colleague (CC). Should take Student (TO)."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail2.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"

    rec1 = create_recipient("colleague@th-koeln.de", "Erika Musterfrau", 2) # CC
    rec2 = create_recipient("student@smail.th-koeln.de", "Max Mustermann", 1) # TO
    mock_msg.recipients = [rec1, rec2]

    mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "SentItems"
    assert moved[0]["lastname"] == "Mustermann"

def test_inbox_from_student_with_cc(mock_dependencies, tmp_path):
    """Test: Student sends to User with another student in CC. Should take Sender."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail3.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "Max Mustermann <mustermann@smail.th-koeln.de>"

    rec1 = create_recipient("daniel.gaida@th-koeln.de", "Daniel Gaida", 1) # TO
    rec2 = create_recipient("other_student@smail.th-koeln.de", "Erika Musterfrau", 2) # CC
    mock_msg.recipients = [rec1, rec2]

    mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "Inbox"
    assert moved[0]["lastname"] == "Mustermann" # The sender

def test_inbox_from_external_to_user_and_student(mock_dependencies, tmp_path):
    """Test: External sends to User and Student. Should take Sender's lastname."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail4.msg").touch()

    mock_msg = MagicMock()
    # Using 'External, Name' to ensure extract_lastname returns 'External'
    mock_msg.sender = "External, Name <external@gmail.com>"

    rec1 = create_recipient("daniel.gaida@th-koeln.de", "Daniel Gaida", 1) # TO
    rec2 = create_recipient("student@smail.th-koeln.de", "Max Mustermann", 1) # TO
    mock_msg.recipients = [rec1, rec2]

    mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "Inbox"
    assert moved[0]["lastname"] == "External"

def test_sent_items_multiple_to_and_cc(mock_dependencies, tmp_path):
    """Test: User sends to 2 students (TO) and 1 person (CC). Should take first student (TO)."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail5.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"

    rec1 = create_recipient("student1@smail.th-koeln.de", "Max Mustermann", 1) # TO
    rec2 = create_recipient("student2@smail.th-koeln.de", "Erika Musterfrau", 1) # TO
    rec3 = create_recipient("cc@th-koeln.de", "CC Person", 2) # CC
    mock_msg.recipients = [rec1, rec2, rec3]

    mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "SentItems"
    assert moved[0]["lastname"] == "Mustermann"

def test_sent_items_fallback_to_second_to(mock_dependencies, tmp_path):
    """Test: User sends to invalid name (TO) and Student (TO). Should take Student."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "mail6.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"

    # Mocking extract_lastname to return "Unknown" for "Unknown" name
    with patch('mcp_university.classifier.sort_emails.extract_lastname') as mock_extract:
        mock_extract.side_effect = lambda x: "Unknown" if "Unknown" in str(x) else "Mustermann"

        rec1 = create_recipient("unknown@some.com", "Unknown", 1) # TO
        rec2 = create_recipient("student@smail.th-koeln.de", "Max Mustermann", 1) # TO
        mock_msg.recipients = [rec1, rec2]

        mock_dependencies["open_msg"].return_value.__enter__.return_value = mock_msg

        config = {"BachelorThesis": str(tmp_path / "target")}
        moved = process_emails(source_root, Path("dummy"), config)

        assert moved[0]["folder"] == "SentItems"
        assert moved[0]["lastname"] == "Mustermann"
