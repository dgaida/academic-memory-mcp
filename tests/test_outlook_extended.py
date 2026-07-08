"""Tests for test_outlook_extended.py."""
from unittest.mock import MagicMock, patch
from mcp_university.utils.outlook import is_outlook_open, create_outlook_draft

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
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True),          patch('mcp_university.utils.outlook.is_outlook_open', return_value=False):
        assert create_outlook_draft("Sub", "Body") is False

def test_create_outlook_draft_success(tmp_path):
    """Test create_outlook_draft success case."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True),          patch('mcp_university.utils.outlook.is_outlook_open', return_value=True),          patch('win32com.client.Dispatch') as mock_dispatch,          patch('mcp_university.utils.outlook.get_config') as mock_get_config:
        
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
        
        # Use MagicMock for the mail item
        mock_mail = MagicMock()
        mock_mail.Attachments = MagicMock()
        mock_mail.Save = MagicMock()
        mock_mail.Display = MagicMock()

        mock_folder.Items.Add.return_value = mock_mail
        mock_outlook.CreateItem.return_value = mock_mail
        
        attachment = tmp_path / "test.txt"
        attachment.write_text("hello")
        
        res = create_outlook_draft("Sub", "Body", "to@test.com", ["cc@test.com"], [attachment])
        
        assert res is True
        assert mock_mail.Subject == "Sub"
        assert mock_mail.To == "to@test.com"
        assert mock_mail.CC == "cc@test.com"
        mock_mail.Attachments.Add.assert_called_once()
        mock_mail.Save.assert_called_once()

def test_create_outlook_draft_exception():
    """Test create_outlook_draft exception handling."""
    with patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True),          patch('mcp_university.utils.outlook.is_outlook_open', return_value=True),          patch('win32com.client.Dispatch') as mock_dispatch:

        # Mock Dispatch to succeed but GetNamespace to fail
        mock_outlook = mock_dispatch.return_value
        mock_outlook.GetNamespace.side_effect = Exception("Namespace failed")

        assert create_outlook_draft("Sub", "Body") is False
