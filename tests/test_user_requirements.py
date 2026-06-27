import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import project modules. We assume CI has dependencies or we use localized mocking if needed.
# Since ruff failed on E402, we put imports at top.
from mcp_university.classifier.sort_emails import extract_lastname, process_emails

def create_recipient(email, name, r_type):
    rec = MagicMock()
    rec.email = email
    rec.name = name
    rec.type = r_type
    return rec

@pytest.fixture
def mock_deps():
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
            "move": mock_move,
            "config": mock_config
        }

def test_requirement_1_name_extraction():
    """Requirement 1: Specific folder name extraction tests."""
    test_cases = [
        ("Nils Hans Morz <nils_hans.morz@smail.th-koeln.de>", "Morz"),
        ("'Anna Pizza Sibel' <anna.pizza_sibel@smail.th-koeln.de>", "Pizza Sibel"),
        ("'Sam Josh Strich' <sam_josh.strich@smail.th-koeln.de>", "Strich"),
        ("'Digital Science (Ma) Management Board' <digital-science@f10.th-koeln.de>", "Digital-Science"),
        ("eRechnung TH Köln <kreditorenbuchhaltung@th-koeln.de>", "Kreditorenbuchhaltung"),
        ("TH // chris.hase@th-koeln.de", "Hase"),
        ("'Eva Adam | Hans GmbH' <eva.adam@hans-gmbh.com>", "Adam"),
    ]

    for input_str, expected in test_cases:
        actual = extract_lastname(input_str)
        assert actual == expected, f"Failed for {input_str}: expected {expected}, got {actual}"

def test_requirement_2_cc_inbox(mock_deps, tmp_path):
    """Requirement 2: Received in CC should be in Inbox."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "cc_received.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "Student Name <student@smail.th-koeln.de>"
    # User is in CC
    rec1 = create_recipient("other@smail.th-koeln.de", "Other Student", 1) # TO
    rec2 = create_recipient("daniel.gaida@th-koeln.de", "Daniel Gaida", 2) # CC
    mock_msg.recipients = [rec1, rec2]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "Inbox"
    # Sender is "Student Name" -> "Name"
    assert moved[0]["lastname"] == "Name"

def test_requirement_2_cc_sent_self(mock_deps, tmp_path):
    """Requirement 2: User sends and puts self in CC -> SentItems, folder is first recipient."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "cc_sent_self.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"
    # User in CC
    rec1 = create_recipient("student@smail.th-koeln.de", "Max Mustermann", 1) # TO
    rec2 = create_recipient("daniel.gaida@th-koeln.de", "Daniel Gaida", 2) # CC
    mock_msg.recipients = [rec1, rec2]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "SentItems"
    assert moved[0]["lastname"] == "Mustermann"

def test_requirement_3_inbox_cases(mock_deps, tmp_path):
    """Requirement 3: Specific Inbox storage tests."""
    source_root = tmp_path / "source"
    source_root.mkdir()

    test_cases = [
        ("Sabine Sua <ssua@fuse.com>", "Sua"),
        ("Alex Dampf <alex.dampf@hs-burg.de>", "Dampf"),
    ]

    for sender, expected_lastname in test_cases:
        msg_name = f"{expected_lastname}.msg"
        (source_root / msg_name).touch()

        mock_msg = MagicMock()
        mock_msg.sender = sender
        mock_msg.recipients = [create_recipient("daniel.gaida@th-koeln.de", "Daniel Gaida", 1)]

        mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg

        config = {"BachelorThesis": str(tmp_path / "target")}
        moved = process_emails(source_root, Path("dummy"), config)

        # Finding the moved entry for this msg
        entry = next(e for e in moved if Path(e["path"]).name == msg_name)
        assert entry["folder"] == "Inbox"
        assert entry["lastname"] == expected_lastname

def test_requirement_4_sent_items_prioritization(mock_deps, tmp_path):
    """Requirement 4: Sent to Eva Adam (TO) and Hans Dampf (CC) -> Adam/SentItems."""
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "sent_to_adam.msg").touch()

    mock_msg = MagicMock()
    mock_msg.sender = "daniel.gaida@th-koeln.de"

    rec1 = create_recipient("eva.adam@hans-gmbh.com", "Eva Adam | Hans GmbH", 1) # TO
    rec2 = create_recipient("hans.dampf@th-koeln.de", "hans.dampf@th-koeln.de", 2) # CC
    mock_msg.recipients = [rec1, rec2]

    mock_deps["open_msg"].return_value.__enter__.return_value = mock_msg

    config = {"BachelorThesis": str(tmp_path / "target")}
    moved = process_emails(source_root, Path("dummy"), config)

    assert moved[0]["folder"] == "SentItems"
    assert moved[0]["lastname"] == "Adam"
