"""Tests for test_outlook_extended.py."""

import sys
import subprocess
from importlib import reload
from unittest.mock import MagicMock, patch
from mcp_university.utils.outlook import is_outlook_open, create_outlook_draft


def test_outlook_imports_reload():
    """Test OUTLOOK_AVAILABLE is False when win32com is not available."""
    with patch.dict("sys.modules", {"win32com": None, "win32com.client": None}):
        import mcp_university.utils.outlook as outlook_mod
        reload(outlook_mod)
        assert outlook_mod.OUTLOOK_AVAILABLE is False

    # Restore the module state
    import mcp_university.utils.outlook as outlook_mod
    reload(outlook_mod)


def test_is_outlook_open_windows():
    """Test is_outlook_open on Windows."""
    with patch('platform.system', return_value='Windows'):
        with patch('subprocess.check_output', return_value=b'outlook.exe 1234'):
            assert is_outlook_open() is True
        with patch('subprocess.check_output', return_value=b'none'):
            assert is_outlook_open() is False


def test_is_outlook_open_darwin():
    """Test is_outlook_open on macOS."""
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.check_call', return_value=0):
            assert is_outlook_open() is True
        # Raise CalledProcessError to cover line 41
        with patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(1, "pgrep")):
            assert is_outlook_open() is False
        with patch('subprocess.check_call', side_effect=Exception()):
            assert is_outlook_open() is False


def test_is_outlook_open_other():
    """Test is_outlook_open on other systems."""
    with patch('platform.system', return_value='Linux'):
        assert is_outlook_open() is False


def test_create_outlook_draft_no_outlook_available():
    """Test create_outlook_draft when Outlook is not available."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', False):
        assert create_outlook_draft("Sub", "Body") is False


def test_create_outlook_draft_not_open():
    """Test create_outlook_draft when Outlook is not open."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True), \
         patch('mcp_university.utils.outlook.is_outlook_open', return_value=False):
        assert create_outlook_draft("Sub", "Body") is False


def test_create_outlook_draft_success(tmp_path):
    """Test create_outlook_draft success case."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True), \
         patch('mcp_university.utils.outlook.is_outlook_open', return_value=True), \
         patch('mcp_university.utils.outlook.win32com.client.Dispatch') as mock_dispatch, \
         patch('mcp_university.utils.outlook.get_config') as mock_get_config:
        
        mock_cfg = MagicMock()
        mock_cfg.user.email = "test@example.com"
        mock_get_config.return_value = mock_cfg
        
        mock_outlook = mock_dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value
        
        mock_store = MagicMock()
        mock_store.DisplayName = "test@example.com"
        mock_ns.Stores = [mock_store]
        
        mock_root = mock_store.GetRootFolder.return_value
        mock_folder = MagicMock()
        mock_folder.Name = "Work in Progress"
        mock_root.Folders = [mock_folder]
        
        class SimpleMail:
            """Mock SimpleMail helper class."""

            def __init__(self):
                """Initialize mock mail attributes."""
                self.Subject = None
                self.To = None
                self.CC = None
                self.Body = None
                self.Attachments = MagicMock()
                self.Save = MagicMock()
                self.Display = MagicMock()

        mock_mail = SimpleMail()
        mock_folder.Items.Add.return_value = mock_mail
        mock_outlook.CreateItem.return_value = mock_mail
        
        attachment = tmp_path / "test.txt"
        attachment.write_text("hello")
        
        res = create_outlook_draft("Sub", "Body", "to@test.com", ["cc@test.com"], [attachment])
        
        assert res is True
        assert mock_mail.Subject == "Sub"
        assert mock_mail.To == "to@test.com"
        assert mock_mail.CC == "cc@test.com"
        mock_mail.Save.assert_called_once()


def test_create_outlook_draft_inbox_subfolder(tmp_path):
    """Test create_outlook_draft searching inside Posteingang/Inbox subfolders."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True), \
         patch('mcp_university.utils.outlook.is_outlook_open', return_value=True), \
         patch('mcp_university.utils.outlook.win32com.client.Dispatch') as mock_dispatch, \
         patch('mcp_university.utils.outlook.get_config') as mock_get_config:

        mock_cfg = MagicMock()
        mock_cfg.user.email = "test@example.com"
        mock_get_config.return_value = mock_cfg

        mock_outlook = mock_dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_store = MagicMock()
        mock_store.DisplayName = "test@example.com"
        mock_ns.Stores = [mock_store]

        mock_root = mock_store.GetRootFolder.return_value

        # We have two root folders: "Inbox" and "Other"
        # "Inbox" contains subfolder "Work in Progress"
        mock_inbox = MagicMock()
        mock_inbox.Name = "Inbox"

        mock_work_folder = MagicMock()
        mock_work_folder.Name = "Work in Progress"
        mock_inbox.Folders = [mock_work_folder]

        mock_other = MagicMock()
        mock_other.Name = "Some Other Folder"
        mock_other.Folders = []

        mock_root.Folders = [mock_other, mock_inbox]

        class SimpleMail:
            """Mock SimpleMail helper class."""

            def __init__(self):
                """Initialize mock mail attributes."""
                self.Subject = None
                self.To = None
                self.CC = None
                self.Body = None
                self.Attachments = MagicMock()
                self.Save = MagicMock()
                self.Display = MagicMock()

        mock_mail = SimpleMail()
        mock_work_folder.Items.Add.return_value = mock_mail
        mock_outlook.CreateItem.return_value = mock_mail

        res = create_outlook_draft("Sub", "Body", "to@test.com")

        assert res is True
        assert mock_mail.Subject == "Sub"
        mock_mail.Save.assert_called_once()


def test_create_outlook_draft_search_exception():
    """Test create_outlook_draft logging a warning on search exceptions."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True), \
         patch('mcp_university.utils.outlook.is_outlook_open', return_value=True), \
         patch('mcp_university.utils.outlook.win32com.client.Dispatch') as mock_dispatch, \
         patch('mcp_university.utils.outlook.get_config') as mock_get_config:

        mock_cfg = MagicMock()
        mock_cfg.user.email = "test@example.com"
        mock_get_config.return_value = mock_cfg

        mock_outlook = mock_dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        # Accessing Stores raises exception to trigger lines 108-109 warning
        type(mock_ns).Stores = property(lambda self: Exception("MAPI Store failure"))

        class SimpleMail:
            """Mock SimpleMail helper class."""

            def __init__(self):
                """Initialize mock mail attributes."""
                self.Subject = None
                self.To = None
                self.CC = None
                self.Body = None
                self.Attachments = MagicMock()
                self.Save = MagicMock()
                self.Display = MagicMock()

        mock_mail = SimpleMail()
        mock_outlook.CreateItem.return_value = mock_mail

        res = create_outlook_draft("Sub", "Body")
        assert res is True  # Falls back to standard Drafts via CreateItem


def test_create_outlook_draft_exception():
    """Test create_outlook_draft exception handling."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True), \
         patch('mcp_university.utils.outlook.is_outlook_open', return_value=True), \
         patch('mcp_university.utils.outlook.win32com.client.Dispatch') as mock_dispatch:

        mock_dispatch.side_effect = Exception("Dispatch failed")
        assert create_outlook_draft("Sub", "Body") is False
