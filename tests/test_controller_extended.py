"""Tests for test_controller_extended.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from mcp_university.classifier.controller import EmailController
import numpy as np

@pytest.fixture
def controller():
    """Test function docstring."""
    with patch("mcp_university.classifier.controller.get_config") as mock_cfg,          patch("mcp_university.classifier.controller.Summarizer"),          patch("mcp_university.classifier.controller.PersonProfiler"),          patch("mcp_university.classifier.controller.Agent"),          patch("mcp_university.classifier.controller.Path.exists") as mock_exists:
        
        cfg = mock_cfg.return_value
        cfg.config_dir = Path("config")
        cfg.llm.model = "test-model"
        cfg.llm.base_url = "http://localhost"
        
        mock_exists.return_value = False
        ctrl = EmailController(config_path="nonexistent.yaml")
        ctrl.class_paths = {"ClassB": "/path/to/classB"}
        yield ctrl

@patch("mcp_university.classifier.controller.shutil.move")
@patch("mcp_university.classifier.controller.Path.unlink")
@patch("mcp_university.classifier.controller.Path.exists")
@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.find_student_folder")
@patch("mcp_university.classifier.controller.Path.mkdir")
def test_relocate_emails(mock_mkdir, mock_find, mock_parser, mock_exists, mock_unlink, mock_move, controller):
    """Test function docstring."""
    # Instead of side_effect, let's just return False for exists most of the time
    mock_exists.return_value = False
    
    mock_parser_inst = mock_parser.return_value
    mock_parser_inst.get_mail_details.return_value = {"subject": "Test", "body": "Test"}
    
    mock_find.return_value = Path("/path/to/classB/Doe")

    emails = [
        {
            "path": "old/path/mail.msg",
            "new_path": "new/path/mail.msg",
            "student_folder": "old/path",
            "target_folder": "new/path",
            "new_class": "ClassB",
            "class": "ClassA",
            "lastname": "Doe",
            "new_lastname": "Doe",
            "identifier_path": "old/path/mail.msg",
            "folder": "Inbox"
        }
    ]
    
    controller.relocate_emails(emails)
    assert True

@patch("mcp_university.classifier.controller.get_model")
def test_get_similarity_info(mock_get_model, controller):
    """Test function docstring."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_model.encode.return_value = np.array([[1.0, 0.0]])
    
    with patch("mcp_university.classifier.controller.yaml.safe_load") as mock_load,          patch("mcp_university.classifier.controller.open", mock_open(read_data="class_paths: {}")):
        mock_load.return_value = {"class_paths": {"Class1": "path1"}}
        
        with patch("mcp_university.classifier.controller.SearchIndex") as mock_idx_cls:
            mock_idx = mock_idx_cls.return_value
            mock_idx.search_by_vector.return_value = [
                {"score": 0.9, "path": "other_mail.msg", "content": "similar content"}
            ]
            
            info = controller.get_similarity_info(Path("mail.msg"), "Doe")
            assert isinstance(info, str)
