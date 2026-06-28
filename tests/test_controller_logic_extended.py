"""Tests for test_controller_logic_extended.py."""
import pytest
import yaml
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.classifier.controller import EmailController
from datetime import datetime

@pytest.fixture
def mock_controller_deps(tmp_path):
    """Test function docstring."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Paths for config files
    config_path = config_dir / "folders.yaml"
    memory_config_path = config_dir / "classifier_memory_paths.yaml"

    class_paths = {"Exam": str(tmp_path / "exams")}
    with open(config_path, "w") as f:
        yaml.dump({"class_paths": class_paths}, f)
        
    memory_paths = {"Exam": "exam_memory"}
    with open(memory_config_path, "w") as f:
        yaml.dump({"class_paths": memory_paths}, f)
    
    # Patch the controller to use this path
    with patch("mcp_university.classifier.controller.MEMORY_CONFIG_PATH", memory_config_path):
        with patch('mcp_university.classifier.controller.get_config') as mock_get_config:
            mock_cfg = MagicMock()
            mock_cfg.config_dir = config_dir
            mock_cfg.data_dir = tmp_path / "data"
            mock_cfg.data_dir.mkdir()
            mock_cfg.embeddings.model = "test-emb-model"
            mock_cfg.user.emails = ["prof@th-koeln.de"]
            mock_get_config.return_value = mock_cfg

            with patch('mcp_university.classifier.controller.MCPAgent'),                  patch('mcp_university.classifier.controller.Agent'),                  patch('mcp_university.classifier.controller.Summarizer'):
                controller = EmailController(config_path=str(config_path))
                # Manually inject memory index
                controller.class_to_memory_index = {"Exam": "exam_memory"}
                yield controller, mock_cfg

def test_get_memory_context_not_configured(mock_controller_deps):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    res = controller._get_memory_context("content", "UnknownClass")
    assert res == ""

def test_get_memory_context_success(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, cfg = mock_controller_deps
    
    # Setup memory index dir
    index_dir = cfg.data_dir / "memory" / "exam_memory"
    index_dir.mkdir(parents=True)
    
    mock_summarizer = controller.summarizer
    mock_summarizer.client.chat.return_value = {
        "message": {"content": "Question 1\nQuestion 2\nQuestion 3"}
    }
    
    with patch('mcp_university.classifier.controller.SearchIndex') as mock_index_cls:
        mock_index = mock_index_cls.return_value
        mock_index.search.return_value = [{"content": "Relevant answer", "score": 0.9}]
        
        res = controller._get_memory_context("I have a question about the exam.", "Exam")
        
        assert "RELEVANTE INFORMATIONEN" in res
        assert "Relevant answer" in res

def test_get_memory_context_exception(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, cfg = mock_controller_deps
    index_dir = cfg.data_dir / "memory" / "exam_memory"
    index_dir.mkdir(parents=True)
    
    controller.summarizer.client.chat.side_effect = Exception("LLM fail")
    res = controller._get_memory_context("content", "Exam")
    assert res == ""

def test_get_similarity_info_error_path(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    
    # Create a dummy email file
    email_file = tmp_path / "email.msg"
    email_file.write_text("dummy")
    
    # Create another email file for the same student
    student_dir = tmp_path / "exams" / "2024_WS" / "Mustermann"
    student_dir.mkdir(parents=True)
    other_mail = student_dir / "other.msg"
    other_mail.write_text("other")

    # This will trigger the exception in get_similarity_info
    with patch('mcp_university.classifier.controller.get_model', return_value=None):
        with patch.object(controller.mail_parser, 'get_email_details', side_effect=[
            {"subject": "Subject"},
            {"subject": "Other Subject"}
        ]):
            with patch.object(controller.mail_parser, 'get_email_date', return_value=datetime.now()):
                res = controller.get_similarity_info(email_file, "Mustermann")
                assert "Fehler bei Similarity-Suche" in res

def test_classify_action_success(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    mail_path = tmp_path / "action.msg"
    mail_path.write_text("Hello")
    
    with patch.object(controller.mail_parser, 'parse', return_value="Hello"),          patch.object(controller.mail_parser, 'extract_latest_message', return_value="Hello"),          patch.object(controller.agent, 'chat', return_value="3"):
        
        # 3 is option 3 (index 2)
        idx = controller.classify_action(mail_path, "Context")
        assert idx == 3

def test_classify_action_fallback(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    mail_path = tmp_path / "action.msg"
    mail_path.write_text("Hello")
    
    with patch.object(controller.agent, 'chat', side_effect=Exception("Agent error")):
        idx = controller.classify_action(mail_path, "Context")
        assert idx == 0

def test_execute_action_archive(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    res = controller.execute_action(3, tmp_path / "mail.msg", {})
    assert "archiviert" in res

def test_execute_action_reply(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    # 0 = olMailItem reply
    with patch.object(controller, 'generate_reply', return_value=("Subject", "Draft", False)):
        with patch('mcp_university.classifier.controller.create_outlook_draft', return_value=True):
            res = controller.execute_action(0, tmp_path / "mail.msg", {"lastname": "Mustermann"})
            assert "Outlook Entwurf erstellt" in res

def test_generate_reply_archive(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    mail_path = tmp_path / "mail.msg"
    mail_path.write_text("content")
    
    # 3 = archive
    res = controller.generate_reply(mail_path, "summary", Path("skill"), "doc", Path("persona"), "ctx", Path("apt"), "Sender", "student@test.de", action_idx=3)
    assert res == ("NO_REPLY_NEEDED", "Archivieren", False)

def test_run_sort_no_model(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    with patch('mcp_university.classifier.controller.resolve_model_path', return_value=Path("nonexistent.pkl")):
        with pytest.raises(FileNotFoundError):
            controller.run_sort(str(tmp_path))

def test_parse_report_simple(mock_controller_deps, tmp_path):
    """Test function docstring."""
    controller, _ = mock_controller_deps
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte E-Mails\n\n## ClassA\n| Semester | Nachname | Ordner | Datei |\n| --- | --- | --- | --- |\n| 2024_WS | Name | Inbox | path/to/mail.msg |\n")
    
    emails = controller.parse_report(report)
    assert len(emails) == 1
    assert emails[0]["class"] == "ClassA"
    assert emails[0]["lastname"] == "Name"
