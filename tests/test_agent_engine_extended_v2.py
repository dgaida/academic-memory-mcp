"""Tests for test_agent_engine_extended_v2.py."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.agent.engine import Agent

@pytest.fixture
def mock_agent_deps_v2():
    """Test function docstring."""
    with patch('mcp_university.agent.engine.ParserFactory'),          patch('mcp_university.agent.engine.MetadataStore'),          patch('mcp_university.agent.engine.SearchIndex'),          patch('mcp_university.agent.engine.get_config') as mock_get_config,          patch('mcp_university.agent.engine.LLMClientWrapper'),          patch('mcp_university.agent.engine.Anonymizer'):

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_cfg.user.email = "me@example.com"
        mock_cfg.calendar.send_invitations_automatically = False
        mock_cfg.data_dir = Path("/tmp")
        mock_get_config.return_value = mock_cfg

        yield mock_cfg

def test_agent_init_cloud(mock_agent_deps_v2):
    """Test function docstring."""
    with patch('mcp_university.agent.engine.LLMClientWrapper') as mock_llm:
        agent = Agent(use_cloud=True, cloud_provider="openai", api_key="sk-123")
        assert agent.use_cloud is True
        mock_llm.assert_called_with(provider="openai", model="gpt-4o", api_key="sk-123")

def test_tool_read_file_not_found(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=False):
        res = agent._tool_read_file("nonexistent.txt")
        assert "nicht gefunden" in res

def test_tool_search_documents_no_results(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    agent.index.search.return_value = []
    res = agent._tool_search_documents("query")
    assert "Keine relevanten Dokumente gefunden" in res

def test_tool_get_student_info_not_found(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    mock_conn = agent.store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    res = agent._tool_get_student_info("Nobody")
    assert "Kein Student" in res

def test_tool_get_appointment_slots_missing(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=False):
        res = agent._tool_get_appointment_slots()
        assert "nicht gefunden" in res

def test_tool_get_appointment_slots_error(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True),          patch('pathlib.Path.read_text', side_effect=Exception("Read error")):
        res = agent._tool_get_appointment_slots()
        assert "Fehler beim Lesen" in res

def test_tool_manage_calendar_appointment_invalid_times(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    # Mock win32com to avoid ImportError before reaching the time check
    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_accounts = MagicMock()
        mock_accounts.Count = 1
        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_accounts.Item.return_value = mock_account
        mock_ns.Accounts = mock_accounts

        mock_folder = MagicMock()
        mock_folder.Name = "Kalender (Nur dieser Computer)"
        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_folders = MagicMock()
        mock_folders.Count = 1
        mock_folders.Item.return_value = mock_folder
        mock_root.Folders = mock_folders

        res = agent._tool_manage_calendar_appointment("2030-10-01 11:00", "2030-10-01 10:00", "Sub", "s@t.com")
        assert "muss nach dem Beginn" in res

def test_tool_manage_calendar_appointment_no_pywin32(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('builtins.__import__', side_effect=ImportError("pywin32 missing")):
        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 11:00", "Sub", "s@t.com")
        assert "pywin32 ist nicht installiert" in res

def test_tool_save_email_attachments_not_found(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=False):
        res = agent._tool_save_email_attachments("no.msg")
        assert "nicht gefunden" in res

def test_tool_save_email_attachments_success(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True),          patch('mcp_university.parser.mail_parser.MailParser') as mock_parser_cls:

        mock_parser = mock_parser_cls.return_value
        mock_parser.save_attachments.return_value = [Path("att1.pdf")]

        res = agent._tool_save_email_attachments("email.msg")
        assert "ERFOLG" in res
        assert "att1.pdf" in res

def test_agent_chat_cloud_anonymization(mock_agent_deps_v2):
    """Test function docstring."""
    # This matches self.use_cloud and self.anonymizer in engine.py:435
    with patch('mcp_university.agent.engine.LLMClientWrapper') as mock_llm_class:
        mock_llm = mock_llm_class.return_value
        mock_llm.model = "m"

        agent = Agent(use_cloud=True)
        agent.anonymizer = MagicMock()
        agent.anonymizer.anonymize.side_effect = lambda text, n, e: f"ANON_{text}"
        agent.anonymizer.deanonymize_text.side_effect = lambda text: f"DEANON_{text}"
        agent.anonymizer.mapping = {"P": "O"}

        mock_llm.chat.return_value = {'message': {'content': 'Result'}}

        res = agent.chat([{'role': 'user', 'content': 'Hello'}], sender_name="N", sender_email="e@e.com")

        assert "DEANON_Result" in res
        agent.anonymizer.anonymize.assert_called()

def test_agent_chat_max_iterations(mock_agent_deps_v2):
    """Test function docstring."""
    agent = Agent()
    agent.client.chat.return_value = {
        'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'c', 'function': {'name': 'read_file', 'arguments': {'path': 'f'}}}]
        }
    }
    # Always returning tool calls will hit max_iterations=5
    res = agent.chat([{'role': 'user', 'content': 'Loop'}])
    assert "Maximale Anzahl an Iterationen erreicht" in res
