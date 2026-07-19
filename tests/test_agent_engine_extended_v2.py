"""Tests for test_agent_engine_extended_v2.py."""
import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.agent.engine import Agent

@pytest.fixture
def mock_agent_deps_v2():
    """Test function docstring."""
    with patch('mcp_university.agent.engine.ParserFactory'), \
         patch('mcp_university.agent.engine.MetadataStore') as mock_metadata_store, \
         patch('mcp_university.metadata.store.MetadataStore') as mock_metadata_store_core, \
         patch('mcp_university.agent.engine.SearchIndex'), \
         patch('mcp_university.agent.engine.get_config') as mock_get_config, \
         patch('mcp_university.agent.engine.LLMClientWrapper'), \
         patch('mcp_university.agent.engine.Anonymizer'):

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_cfg.user.email = "me@example.com"
        mock_cfg.calendar.send_invitations_automatically = False
        mock_cfg.calendar.appointment_slots_path = "data/free_slots.md"
        mock_cfg.config_dir = Path("/tmp")
        mock_cfg.data_dir = Path("/tmp")
        mock_cfg.sqlite_path = Path("/tmp/mock_sqlite.db")
        mock_get_config.return_value = mock_cfg

        yield mock_metadata_store, mock_metadata_store_core, mock_cfg

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
    mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
    agent = Agent()
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock.return_value._get_connection.return_value.__enter__.return_value
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
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', side_effect=Exception("Read error")):
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
    with patch('pathlib.Path.exists', return_value=True), \
         patch('mcp_university.parser.mail_parser.MailParser') as mock_parser_cls:

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

def test_tool_read_file_success(mock_agent_deps_v2):
    """Test read_file tool with successful parsing."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True):
        agent.parser_factory.parse.return_value = "Content of the file"
        res = agent._tool_read_file("test.txt")
        assert res == "Content of the file"

        # Parser returns empty/None
        agent.parser_factory.parse.return_value = None
        res = agent._tool_read_file("test.txt")
        assert "Fehler" in res

def test_tool_search_documents_success(mock_agent_deps_v2):
    """Test search_documents tool with mock results."""
    agent = Agent()
    agent.index.search.return_value = [
        {"filename": "test.pdf", "score": 0.95, "content": "Found content"}
    ]
    res = agent._tool_search_documents("query")
    assert "test.pdf" in res
    assert "0.95" in res
    assert "Found content" in res

def test_tool_get_student_info_success(mock_agent_deps_v2):
    """Test get_student_info tool with successful DB retrieval."""
    mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
    agent = Agent()
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock.return_value._get_connection.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = (1, "Max Mustermann", "max@stud.de", "Thesis Topic", "Registered", 101, "/path/to/folder")

    res = agent._tool_get_student_info("Max")
    assert "Student: Max Mustermann" in res
    assert "Email: max@stud.de" in res
    assert "Thema: Thesis Topic" in res
    assert "Status: Registered" in res
    assert "Ordner: /path/to/folder" in res

def test_tool_get_appointment_slots_success(mock_agent_deps_v2):
    """Test get_appointment_slots tool with successful reading."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="Slots details") as mock_read:
        res = agent._tool_get_appointment_slots()
        assert res == "Slots details"
        mock_read.assert_called_once()

def test_tool_save_email_attachments_no_attachments(mock_agent_deps_v2):
    """Test save_email_attachments tool returning no attachments."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True), \
         patch('mcp_university.parser.mail_parser.MailParser') as mock_parser_cls:
        mock_parser = mock_parser_cls.return_value
        mock_parser.save_attachments.return_value = []
        res = agent._tool_save_email_attachments("email.msg")
        assert "Keine Anhänge" in res

def test_tool_save_email_attachments_exception(mock_agent_deps_v2):
    """Test save_email_attachments tool throwing an exception."""
    agent = Agent()
    with patch('pathlib.Path.exists', return_value=True), \
         patch('mcp_university.parser.mail_parser.MailParser') as mock_parser_cls:
        mock_parser = mock_parser_cls.return_value
        mock_parser.save_attachments.side_effect = Exception("Parsing error")
        res = agent._tool_save_email_attachments("email.msg")
        assert "Fehler beim Speichern" in res

def test_tool_create_colloquium_config_success(mock_agent_deps_v2, tmp_path):
    """Test create_colloquium_config when config file already exists or is new."""
    agent = Agent()
    email_file = tmp_path / "Inbox" / "email.msg"
    email_file.parent.mkdir(parents=True, exist_ok=True)
    email_file.write_text("dummy")

    config_path = tmp_path / "config.json"

    # Case 1: Config does not exist yet (creates new from template)
    res = agent._tool_create_colloquium_config(str(email_file), "thesis.pdf")
    assert "ERFOLG" in res
    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["pdf"]["filename"] == "thesis.pdf"
    assert data["task"] == "colloquium"

    # Case 2: Config already exists (updates pdf filename)
    res = agent._tool_create_colloquium_config(str(email_file), "updated_thesis.pdf")
    assert "ERFOLG" in res
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["pdf"]["filename"] == "updated_thesis.pdf"

def test_tool_create_colloquium_config_exception(mock_agent_deps_v2):
    """Test create_colloquium_config exception path."""
    agent = Agent()
    # Passing empty/invalid path should raise an exception or we can mock Path to raise
    with patch('pathlib.Path.parent', side_effect=Exception("Path error")):
        res = agent._tool_create_colloquium_config("invalid_path", "test.pdf")
        assert "Fehler" in res

def test_tool_update_colloquium_config_success(mock_agent_deps_v2, tmp_path):
    """Test update_colloquium_config when config file exists or is new."""
    mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
    agent = Agent()

    student_dir = tmp_path / "StudentFolder"
    student_dir.mkdir()
    config_path = student_dir / "config.json"

    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock.return_value._get_connection.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = [str(student_dir)]

    # Case 1: config.json does not exist yet (creates with defaults)
    res = agent._tool_update_colloquium_config("student@th.de", "12.12.2026", "14:00")
    assert "ERFOLG" in res
    assert config_path.exists()
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["colloquium"]["date"] == "12.12.2026"
    assert data["colloquium"]["time"] == "14:00"

    # Case 2: config.json exists (updates values)
    res = agent._tool_update_colloquium_config("student@th.de", "13.12.2026", "15:00")
    assert "ERFOLG" in res
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["colloquium"]["date"] == "13.12.2026"
    assert data["colloquium"]["time"] == "15:00"

def test_tool_update_colloquium_config_not_found(mock_agent_deps_v2):
    """Test update_colloquium_config when student email is not in DB."""
    mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
    agent = Agent()
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock.return_value._get_connection.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = None

    res = agent._tool_update_colloquium_config("nobody@th.de", "12.12.2026", "14:00")
    assert "Fehler: Kein Ordner" in res

def test_tool_update_colloquium_config_exception(mock_agent_deps_v2):
    """Test update_colloquium_config exception path."""
    mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
    agent = Agent()
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock.return_value._get_connection.return_value.__enter__.return_value
        mock_conn.cursor.side_effect = Exception("DB error")

    res = agent._tool_update_colloquium_config("any@th.de", "12.12.2026", "14:00")
    assert "Fehler" in res

def test_tool_manage_calendar_appointment_detailed(mock_agent_deps_v2):
    """Detailed testing of manage_calendar_appointment covering finding folders, drafts, auto-send, colloquiums and all-day events."""
    agent = Agent()

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        # Accounts setup
        mock_accounts = MagicMock()
        mock_accounts.Count = 1
        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_accounts.Item.return_value = mock_account
        mock_ns.Accounts = mock_accounts

        # Root folder with calendar and "Work in Progress" subfolder
        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_calendar = MagicMock()
        mock_calendar.Name = "Kalender (Nur dieser Computer)"
        mock_calendar.FolderPath = "\\me@example.com\\Calendar"

        mock_wip = MagicMock()
        mock_wip.Name = "Work in Progress"
        mock_wip.FolderPath = "\\me@example.com\\Work in Progress"

        # Set root folders count
        mock_root.Folders.Count = 2
        def get_root_folder_item(idx):
            if idx == 1:
                return mock_calendar
            return mock_wip
        mock_root.Folders.Item.side_effect = get_root_folder_item
        mock_root.Folders.__iter__.return_value = [mock_calendar, mock_wip]

        # Stores loop setup
        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root
        mock_ns.Stores = [mock_store]

        # Case 1: Appointment is already occupied (non-all day event in the way)
        mock_items = MagicMock()
        mock_occupied_item = MagicMock()
        mock_occupied_item.AllDayEvent = False
        mock_items.Restrict.return_value = [mock_occupied_item]
        mock_calendar.Items = mock_items

        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "Meeting", "test@stud.de")
        assert "bereits belegt" in res

        # Case 2: Slot is occupied only by AllDayEvent (should ignore and proceed)
        mock_occupied_item.AllDayEvent = True
        mock_items.Restrict.return_value = [mock_occupied_item]

        # We also need to setup draft appointment adding to WIP folder
        mock_draft_item = MagicMock()
        mock_wip.Items.Add.return_value = mock_draft_item

        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "Meeting", "test@stud.de")
        assert "ERFOLG: Termin-Entwurf" in res
        assert mock_draft_item.Subject == "Meeting"
        assert mock_draft_item.Body == "Terminbestätigung via MCP University System."

        # Case 3: Auto-send enabled
        mock_store, mock_store_core, mock_cfg = mock_agent_deps_v2
        mock_cfg.calendar.send_invitations_automatically = True
        mock_calendar.Items.Add.return_value = mock_draft_item
        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "Meeting", "test@stud.de")
        assert "wurde eingetragen und Einladung an" in res
        mock_draft_item.Send.assert_called_once()

        # Case 4: Is colloquium (should update config automatically)
        mock_cfg.calendar.send_invitations_automatically = False
        with patch.object(agent, "_tool_update_colloquium_config") as mock_update_config:
            res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "Kolloquium", "test@stud.de", is_colloquium=True)
            assert "ERFOLG" in res
            mock_update_config.assert_called_with("test@stud.de", "01.10.2030", "10:00")

def test_agent_chat_with_exceptions_and_edge_cases(mock_agent_deps_v2):
    """Test agent chat error handling when a tool throws various exceptions."""
    agent = Agent()

    # 1. TypeError exception during tool invocation
    agent.client.chat.return_value = {
        'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call1', 'function': {'name': 'read_file', 'arguments': {'wrong_arg': 'val'}}}]
        }
    }
    agent.chat([{'role': 'user', 'content': 'Test'}])
    assert agent.last_tool_error is not None
    assert "Falsche Argumente" in agent.last_tool_error

    # 2. General exception during tool invocation
    agent.client.chat.return_value = {
        'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call2', 'function': {'name': 'read_file', 'arguments': {'path': 'val'}}}]
        }
    }
    with patch.dict(agent.available_tools, {"read_file": MagicMock(side_effect=Exception("Critical tool failure"))}):
        agent.chat([{'role': 'user', 'content': 'Test'}])
        assert agent.last_tool_error is not None
        assert "Critical tool failure" in agent.last_tool_error

    # 3. Tool not available
    agent.client.chat.return_value = {
        'message': {
            'role': 'assistant',
            'tool_calls': [{'id': 'call3', 'function': {'name': 'non_existent_tool', 'arguments': {}}}]
        }
    }
    agent.chat([{'role': 'user', 'content': 'Test'}])
    # Check that loop completes successfully when tool is not found (appends warning to response)

def test_agent_chat_system_prompt_anonymization(mock_agent_deps_v2):
    """Test that chat anonymizes system prompt and mapping works correctly."""
    with patch('mcp_university.agent.engine.LLMClientWrapper') as mock_llm_class:
        mock_llm = mock_llm_class.return_value
        mock_llm.model = "m"

        agent = Agent(use_cloud=True)
        agent.anonymizer = MagicMock()
        agent.anonymizer.anonymize.side_effect = lambda text, n, e: f"ANON_{text}"
        agent.anonymizer.deanonymize_text.side_effect = lambda text: f"DEANON_{text}"
        agent.anonymizer.deanonymize_args.side_effect = lambda args: {"deanonymized": "args"}
        agent.anonymizer.mapping = {"PLACEHOLDER": "ORIGINAL"}

        # Return a tool call to test tool call deanonymization
        mock_llm.chat.side_effect = [
            {
                'message': {
                    'role': 'assistant',
                    'tool_calls': [{'id': 'call1', 'function': {'name': 'read_file', 'arguments': {'path': 'PLACEHOLDER'}}}]
                }
            },
            {
                'message': {
                    'role': 'assistant',
                    'content': 'Anonymized final response with PLACEHOLDER'
                }
            }
        ]

        # Mock read_file tool to return ORIGINAL
        with patch.object(agent, "_tool_read_file", return_value="Result containing ORIGINAL"):
            res = agent.chat([{'role': 'user', 'content': 'Hello'}], system_prompt="System rules", sender_name="N", sender_email="e@e.com")

            # Anonymize should have been called on system prompt and user message
            agent.anonymizer.anonymize.assert_any_call("System rules", "N", "e@e.com")
            agent.anonymizer.anonymize.assert_any_call("Hello", "N", "e@e.com")

            # Final response should have deanonymized content
            assert "DEANON_Anonymized final response with PLACEHOLDER" in res
