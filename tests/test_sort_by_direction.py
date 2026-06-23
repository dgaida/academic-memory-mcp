"""Tests for test_sort_by_direction.py."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.classifier.sort_by_direction import sort_emails_by_direction

@pytest.fixture
def temp_email_dir(tmp_path):
    """Test function."""
    source_dir = tmp_path / "emails"
    source_dir.mkdir()
    return source_dir

def test_sort_emails_inbox(temp_email_dir):
    """Tests test_sort_emails_inbox."""
    # Create a dummy .msg file
    msg_file = temp_email_dir / "test_inbox.msg"
    msg_file.touch()
    
    user_emails = ["me@example.com"]
    
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.sender = "student@example.com"
        mock_open.return_value.__enter__.return_value = mock_msg
        
        stats = sort_emails_by_direction(temp_email_dir, user_emails)
        
    assert stats["Inbox"] == 1
    assert stats["SentItems"] == 0
    assert (temp_email_dir / "Inbox" / "test_inbox.msg").exists()
    assert not msg_file.exists()

def test_sort_emails_sent_items(temp_email_dir):
    """Tests test_sort_emails_sent_items."""
    # Create a dummy .msg file
    msg_file = temp_email_dir / "test_sent.msg"
    msg_file.touch()
    
    user_emails = ["me@example.com"]
    
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.sender = "Me <me@example.com>"
        mock_open.return_value.__enter__.return_value = mock_msg
        
        stats = sort_emails_by_direction(temp_email_dir, user_emails)
        
    assert stats["SentItems"] == 1
    assert stats["Inbox"] == 0
    assert (temp_email_dir / "SentItems" / "test_sent.msg").exists()

def test_sort_emails_existing_file(temp_email_dir):
    """Tests test_sort_emails_existing_file."""
    # Create a dummy .msg file
    msg_file = temp_email_dir / "test.msg"
    msg_file.touch()
    
    # Pre-create the target file
    target_dir = temp_email_dir / "Inbox"
    target_dir.mkdir()
    (target_dir / "test.msg").touch()
    
    user_emails = ["me@example.com"]
    
    with patch("extract_msg.openMsg") as mock_open:
        mock_msg = MagicMock()
        mock_msg.sender = "student@example.com"
        mock_open.return_value.__enter__.return_value = mock_msg
        
        stats = sort_emails_by_direction(temp_email_dir, user_emails)
        
    assert stats["Inbox"] == 1
    assert (target_dir / "test_0.msg").exists()

def test_sort_emails_missing_dir():
    """Tests test_sort_emails_missing_dir."""
    stats = sort_emails_by_direction(Path("/non/existent/path"), ["me@example.com"])
    assert stats["Inbox"] == 0
    assert stats["SentItems"] == 0

def test_sort_emails_error_handling(temp_email_dir):
    """Tests test_sort_emails_error_handling."""
    msg_file = temp_email_dir / "error.msg"
    msg_file.touch()
    
    with patch("extract_msg.openMsg", side_effect=Exception("Failed to open")):
        stats = sort_emails_by_direction(temp_email_dir, ["me@example.com"])
        
    assert stats["Error"] == 1

def test_main_function():
    """Tests test_main_function."""
    with patch("mcp_university.classifier.sort_by_direction.get_config") as mock_get_config,          patch("mcp_university.classifier.sort_by_direction.sort_emails_by_direction") as mock_sort,          patch("argparse.ArgumentParser.parse_args") as mock_args:
        
        mock_config = MagicMock()
        mock_config.user.emails = ["me@example.com"]
        mock_get_config.return_value = mock_config
        
        mock_args.return_value = MagicMock(source_dir="/dummy/dir")
        mock_sort.return_value = {"Inbox": 1, "SentItems": 1, "Error": 0}
        
        from mcp_university.classifier.sort_by_direction import main
        main()
        
        mock_sort.assert_called_once()
