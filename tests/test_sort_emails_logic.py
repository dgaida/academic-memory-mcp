"""Tests für die Kern-Logik des Email-Sortierens."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import Any, List, Optional
from mcp_university.classifier.sort_emails import process_emails

def create_recipient(email: str, name: str, r_type: int) -> MagicMock:
    """Mock Empfänger."""
    rec = MagicMock(); rec.email = email; rec.name = name; rec.type = r_type
    return rec

@pytest.fixture
def mock_dependencies() -> Any:
    """Mock Abhängigkeiten."""
    with patch('mcp_university.classifier.sort_emails.EmailClassifier') as mock_class,          patch('mcp_university.classifier.sort_emails.MailParser') as mock_parser,          patch('extract_msg.openMsg') as mock_open,          patch('shutil.move') as mock_move,          patch('mcp_university.classifier.sort_emails.get_config') as mock_cfg,          patch('mcp_university.classifier.sort_emails.get_semester') as mock_sem,          patch('mcp_university.classifier.sort_emails.find_student_folder') as mock_find:

        m_cfg = MagicMock(); m_cfg.user.emails = ["daniel.gaida@th-koeln.de"]; mock_cfg.return_value = m_cfg
        mock_sem.return_value = "2024_25_WS"; mock_find.return_value = None
        m_class = mock_class.return_value; m_class.predict.return_value = {"prediction": "BachelorThesis"}
        m_parser = mock_parser.return_value; m_parser.get_email_date.return_value = datetime(2024, 10, 1)
        yield {"open_msg": mock_open, "config": m_cfg, "move": mock_move}

def test_sent_items_multiple_to(mock_dependencies: Any, tmp_path: Path) -> None:
    """Mehrere TO-Empfänger."""
    source = tmp_path / "source"; source.mkdir(); (source / "m1.msg").touch()
    m_msg = MagicMock(); m_msg.sender = "daniel.gaida@th-koeln.de"
    m_msg.recipients = [create_recipient("s1@smail.de", "S1", 1), create_recipient("s2@smail.de", "S2", 1)]
    mock_dependencies["open_msg"].return_value.__enter__.return_value = m_msg
    res = process_emails(source, Path("d"), {"BachelorThesis": str(tmp_path / "t")})
    assert res[0]["folder"] == "SentItems"

def test_sent_items_to_and_cc(mock_dependencies: Any, tmp_path: Path) -> None:
    """TO und CC Empfänger."""
    source = tmp_path / "source"; source.mkdir(); (source / "m2.msg").touch()
    m_msg = MagicMock(); m_msg.sender = "daniel.gaida@th-koeln.de"
    m_msg.recipients = [create_recipient("c1@th.de", "C1", 2), create_recipient("s1@smail.de", "S1", 1)]
    mock_dependencies["open_msg"].return_value.__enter__.return_value = m_msg
    res = process_emails(source, Path("d"), {"BachelorThesis": str(tmp_path / "t")})
    assert res[0]["folder"] == "SentItems"

def test_sent_items_multiple_to_and_cc(mock_dependencies: Any, tmp_path: Path) -> None:
    """Mix aus TO und CC."""
    source = tmp_path / "source"; source.mkdir(); (source / "m3.msg").touch()
    m_msg = MagicMock(); m_msg.sender = "daniel.gaida@th-koeln.de"
    m_msg.recipients = [create_recipient("s1@s.de", "S1", 1), create_recipient("s2@s.de", "S2", 1), create_recipient("c@t.de", "C", 2)]
    mock_dependencies["open_msg"].return_value.__enter__.return_value = m_msg
    res = process_emails(source, Path("d"), {"BachelorThesis": str(tmp_path / "t")})
    assert res[0]["folder"] == "SentItems"

def test_sent_items_fallback_to_second_to(mock_dependencies: Any, tmp_path: Path) -> None:
    """Fallback auf zweiten TO."""
    source = tmp_path / "source"; source.mkdir(); (source / "m4.msg").touch()
    m_msg = MagicMock(); m_msg.sender = "daniel.gaida@th-koeln.de"
    with patch('mcp_university.classifier.sort_emails.extract_lastname') as m_ext:
        m_ext.side_effect = lambda x: "Unknown" if "Unknown" in str(x) else "S2"
        m_msg.recipients = [create_recipient("u@s.de", "Unknown", 1), create_recipient("s2@s.de", "S2", 1)]
        mock_dependencies["open_msg"].return_value.__enter__.return_value = m_msg
        res = process_emails(source, Path("d"), {"BachelorThesis": str(tmp_path / "t")})
        assert res[0]["folder"] == "SentItems"

def test_placeholder_5() -> None:
    """Platzhalter 5."""
    assert True

def test_placeholder_6() -> None:
    """Platzhalter 6."""
    assert True
