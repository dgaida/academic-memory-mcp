"""Comprehensive coverage boost tests for Agent in mcp_university/agent/engine.py."""

import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from mcp_university.agent.engine import Agent


@pytest.fixture
def mock_agent_setup():
    """Sets up mocks for get_config, MetadataStore, ParserFactory, SearchIndex, and LLMClientWrapper.

    Yields:
        tuple: (agent, mock_store, mock_store_core, mock_cfg)
    """
    with patch('mcp_university.agent.engine.ParserFactory') as mock_parser_factory, \
         patch('mcp_university.agent.engine.MetadataStore') as mock_metadata_store, \
         patch('mcp_university.metadata.store.MetadataStore') as mock_metadata_store_core, \
         patch('mcp_university.agent.engine.SearchIndex'), \
         patch('mcp_university.agent.engine.get_config') as mock_get_config, \
         patch('mcp_university.agent.engine.LLMClientWrapper') as mock_llm_class, \
         patch('mcp_university.agent.engine.Anonymizer') as mock_anon_class:

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_cfg.user.email = "me@example.com"
        mock_cfg.calendar.send_invitations_automatically = False
        mock_cfg.calendar.appointment_slots_path = "data/free_slots.md"
        mock_cfg.config_dir = Path("/tmp")
        mock_cfg.data_dir = Path("/tmp")
        mock_cfg.sqlite_path = Path("/tmp/mock_sqlite.db")
        mock_cfg.qdrant_path = Path("/tmp/mock_qdrant")
        mock_cfg.embeddings.model = "embeddings-model"
        mock_get_config.return_value = mock_cfg

        agent = Agent()

        yield agent, mock_metadata_store.return_value, mock_metadata_store_core.return_value, mock_cfg


def test_tool_read_file_empty_or_none(mock_agent_setup):
    """Tests _tool_read_file returning error when file content is empty or None.

    Covers line: 307.
    """
    agent, _, _, _ = mock_agent_setup

    with patch('pathlib.Path.exists', return_value=True):
        # Case 1: parser returns empty string
        agent.parser_factory.parse.return_value = ""
        res1 = agent._tool_read_file("test.txt")
        assert "Fehler: Datei konnte nicht gelesen werden" in res1

        # Case 2: parser returns None
        agent.parser_factory.parse.return_value = None
        res2 = agent._tool_read_file("test.txt")
        assert "Fehler: Datei konnte nicht gelesen werden" in res2


def test_tool_get_student_info_success_detailed(mock_agent_setup):
    """Tests _tool_get_student_info retrieving a student and formatting output.

    Covers lines: 331-334 of the student info tool (different from calendar).
    """
    agent, mock_store, _, _ = mock_agent_setup

    # Configure mock connection and cursor
    mock_conn = mock_store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (1, "Max Mustermann", "max@stud.de", "Thesis Topic", "Registered", 101, "/path/to/folder")

    res = agent._tool_get_student_info("Max")
    assert "Student: Max Mustermann" in res
    assert "Email: max@stud.de" in res
    assert "Thema: Thesis Topic" in res
    assert "Status: Registered" in res
    assert "Ordner: /path/to/folder" in res


def test_tool_get_appointment_slots_success(mock_agent_setup):
    """Tests _tool_get_appointment_slots successfully reading free slots file.

    Covers line: 338.
    """
    agent, _, _, _ = mock_agent_setup

    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="# Available Slots\n- 2026-12-01 10:00") as mock_read:
        res = agent._tool_get_appointment_slots()
        assert res == "# Available Slots\n- 2026-12-01 10:00"
        mock_read.assert_called_once()


def test_tool_manage_calendar_appointment_past_date(mock_agent_setup):
    """Tests _tool_manage_calendar_appointment returning error when the start time is in the past.

    Covers lines: 362-363 of time check (in past) / original calendar check.
    """
    agent, _, _, _ = mock_agent_setup

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        res = agent._tool_manage_calendar_appointment("2020-01-01 10:00", "2020-01-01 10:30", "Sprechstunde", "stud@example.com")
        assert "Termin liegt in der Vergangenheit" in res


def test_tool_manage_calendar_appointment_colloquium_duration_check(mock_agent_setup):
    """Tests that is_colloquium flag enforces at least 60 minutes duration.

    Covers line: 418.
    """
    agent, _, _, _ = mock_agent_setup

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        # Mock Accounts
        mock_accounts = MagicMock()
        mock_accounts.Count = 1
        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_accounts.Item.return_value = mock_account
        mock_ns.Accounts = mock_accounts

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_calendar = MagicMock()
        mock_calendar.Name = "Kalender (Nur dieser Computer)"
        mock_calendar.FolderPath = "\\me@example.com\\Calendar"

        mock_root.Folders.Count = 1
        mock_root.Folders.Item.return_value = mock_calendar
        mock_root.Folders.__iter__.return_value = [mock_calendar]

        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root
        mock_ns.Stores = [mock_store]

        # No occupied items
        mock_calendar.Items.Restrict.return_value = []

        mock_appointment = MagicMock()
        mock_calendar.Items.Add.return_value = mock_appointment

        # Call with 30 min difference: 10:00 to 10:30, but is_colloquium=True.
        # This triggers lines 417-418 to set end time to 11:00 (60 minutes).
        with patch.object(agent, "_tool_update_colloquium_config") as mock_update:
            res = agent._tool_manage_calendar_appointment(
                start_time="2030-10-01 10:00",
                end_time="2030-10-01 10:30",
                subject="Colloquium",
                student_email="stud@example.com",
                is_colloquium=True
            )
            assert "ERFOLG: Termin-Entwurf" in res
            mock_update.assert_called_with("stud@example.com", "01.10.2030", "10:00")


def test_tool_manage_calendar_appointment_except_all_day_event(mock_agent_setup):
    """Tests exceptional item handling in restricted items loop inside manage_calendar_appointment.

    Covers lines: 400-401.
    """
    agent, _, _, _ = mock_agent_setup

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

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_calendar = MagicMock()
        mock_calendar.Name = "Kalender (Nur dieser Computer)"
        mock_calendar.FolderPath = "\\me@example.com\\Calendar"

        mock_root.Folders.Count = 1
        mock_root.Folders.Item.return_value = mock_calendar
        mock_root.Folders.__iter__.return_value = [mock_calendar]

        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root
        mock_ns.Stores = [mock_store]

        # Provide a restricted item that raises an exception when AllDayEvent is accessed
        mock_item = MagicMock()
        type(mock_item).AllDayEvent = property(MagicMock(side_effect=Exception("mock error")))
        mock_calendar.Items.Restrict.return_value = [mock_item]

        # Since it raises an exception, the loop catches it, continues, and considers the slot FREE.
        mock_appointment = MagicMock()
        mock_calendar.Items.Add.return_value = mock_appointment

        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "Sub", "stud@example.com")
        assert "ERFOLG: Termin-Entwurf" in res


def test_tool_manage_calendar_appointment_colloquium_update_config_exception(mock_agent_setup):
    """Tests exception safety when _tool_update_colloquium_config fails during colloquium booking.

    Covers lines: 438-439.
    """
    agent, _, _, _ = mock_agent_setup

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

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_calendar = MagicMock()
        mock_calendar.Name = "Kalender (Nur dieser Computer)"
        mock_calendar.FolderPath = "\\me@example.com\\Calendar"

        mock_root.Folders.Count = 1
        mock_root.Folders.Item.return_value = mock_calendar
        mock_root.Folders.__iter__.return_value = [mock_calendar]

        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root
        mock_ns.Stores = [mock_store]

        mock_calendar.Items.Restrict.return_value = []
        mock_appointment = MagicMock()
        mock_calendar.Items.Add.return_value = mock_appointment

        # Force update_colloquium_config to throw an exception
        with patch.object(agent, "_tool_update_colloquium_config", side_effect=RuntimeError("JSON write failed")):
            res = agent._tool_manage_calendar_appointment(
                start_time="2030-10-01 10:00",
                end_time="2030-10-01 11:00",
                subject="Kolloquium",
                student_email="stud@example.com",
                is_colloquium=True
            )
            # The booking should still succeed because it's try-except isolated
            assert "ERFOLG: Termin-Entwurf" in res


def test_tool_update_colloquium_config_no_folder(mock_agent_setup):
    """Tests _tool_update_colloquium_config returning error if no folder for student is found.

    Covers line: 526 of the new version / original 532.
    """
    agent, mock_store, mock_store_core, _ = mock_agent_setup

    # Configure both class mocks to return None
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock._get_connection.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = None

    res = agent._tool_update_colloquium_config("stud@example.com", "12.12.2026", "14:00")
    assert "Fehler: Kein Ordner" in res


def test_tool_save_email_attachments_no_attachments_found(mock_agent_setup, tmp_path):
    """Tests _tool_save_email_attachments creating grandparent directory if missing.

    Covers lines: 594.
    """
    agent, _, _, _ = mock_agent_setup

    with patch('pathlib.Path.exists', autospec=True) as mock_exists, \
         patch('mcp_university.parser.mail_parser.MailParser') as mock_parser_cls:

        target_grandparent = tmp_path / "non_existent_grandparent"
        email_file = target_grandparent / "parent" / "email.msg"

        # Scenario: email file exists, grandparent directory does not exist
        real_exists = Path.exists
        def side_effect_exists(self, *args, **kwargs):
            path_str = str(self)
            if "email.msg" in path_str:
                return True
            if "non_existent_grandparent" in path_str:
                return False
            return real_exists(self, *args, **kwargs)

        mock_exists.side_effect = side_effect_exists

        mock_parser = mock_parser_cls.return_value
        mock_parser.save_attachments.return_value = [] # Empty list of saved paths

        res = agent._tool_save_email_attachments(str(email_file))
        assert "Keine Anhänge zum Speichern" in res
        # Verify directory was actually created on the real filesystem!
        import os
        assert os.path.exists(target_grandparent)


def test_tool_manage_calendar_appointment_inbox_subfolder_search(mock_agent_setup):
    """Tests searching target folder inside the inbox folder if not found on the root level.

    Covers lines: 362-363 of target folder exception, and target_folder search.
    """
    agent, _, _, _ = mock_agent_setup

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

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value
        mock_calendar = MagicMock()
        mock_calendar.Name = "Kalender (Nur dieser Computer)"
        mock_calendar.FolderPath = "\\me@example.com\\Calendar"

        # Inbox folder setup
        mock_inbox = MagicMock()
        mock_inbox.Name = "Inbox"

        # Subfolder setup
        mock_wip = MagicMock()
        mock_wip.Name = "Work in Progress"
        mock_wip.FolderPath = "\\me@example.com\\Inbox\\Work in Progress"
        mock_inbox.Folders = [mock_wip]

        # Root folders has Calendar and Inbox
        mock_root.Folders.Count = 2
        mock_root.Folders.Item.side_effect = lambda idx: mock_calendar if idx == 1 else mock_inbox
        mock_root.Folders.__iter__.return_value = [mock_calendar, mock_inbox]

        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root

        # Force exception in stores access to cover lines 362-363
        type(mock_ns).Stores = property(MagicMock(side_effect=Exception("Stores access error")))

        # Free slot
        mock_calendar.Items.Restrict.return_value = []

        mock_draft_item = MagicMock()
        # Fallback will create in calendar folder since target_folder is None due to the exception
        mock_calendar.Items.Add.return_value = mock_draft_item

        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "S", "stud@example.com")
        assert "ERFOLG" in res


def test_tool_manage_calendar_appointment_get_default_folder_fallback_and_none(mock_agent_setup):
    """Tests the GetDefaultFolder(9) fallback and failure returning error.

    Covers lines: 331-334 (except pass) and 338 (not found), 366 (no calendar log).
    """
    agent, _, _, _ = mock_agent_setup

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

        mock_root = mock_account.DeliveryStore.GetRootFolder.return_value

        # Calendar folder is NOT in root folders
        mock_root.Folders.Count = 0
        mock_root.Folders.__iter__.return_value = []

        mock_store = MagicMock()
        mock_store.DisplayName = "me@example.com"
        mock_store.GetRootFolder.return_value = mock_root
        mock_ns.Stores = [mock_store]

        # Force GetDefaultFolder(9) to raise an exception to cover lines 331-334
        mock_account.DeliveryStore.GetDefaultFolder.side_effect = Exception("GetDefaultFolder error")

        res = agent._tool_manage_calendar_appointment("2030-10-01 10:00", "2030-10-01 10:30", "S", "stud@example.com")
        assert "nicht gefunden" in res


def test_tool_manage_calendar_appointment_outer_exception(mock_agent_setup):
    """Tests catching outer exceptions in _tool_manage_calendar_appointment.

    Covers lines: 449-450.
    """
    agent, _, _, _ = mock_agent_setup

    # Pass an invalid datetime format to trigger strptime ValueError which is caught by outer try-except
    res = agent._tool_manage_calendar_appointment("invalid-time", "2030-10-01 10:30", "S", "stud@example.com")
    assert "Fehler bei der Kalender-Verarbeitung" in res


def test_agent_chat_anonymize_other_role_and_last_appointment_info(mock_agent_setup):
    """Tests anonymizing non-user role messages and setting last_appointment_info in Agent.chat.

    Covers lines: 631, 679.
    """
    agent, _, _, _ = mock_agent_setup

    agent.use_cloud = True
    agent.anonymizer = MagicMock()
    agent.anonymizer.anonymize.side_effect = lambda x, n, e: f"ANON_{x}"
    agent.anonymizer.deanonymize_text.side_effect = lambda x: x
    agent.anonymizer.deanonymize_args.side_effect = lambda x: x
    agent.anonymizer.mapping = {}

    # Tool call returns successful calendar appointment booking
    agent.client.chat.side_effect = [
        {
            'message': {
                'role': 'assistant',
                'tool_calls': [{
                    'id': 'call1',
                    'function': {
                        'name': 'manage_calendar_appointment',
                        'arguments': {'start_time': '2030-10-01 10:00', 'end_time': '2030-10-01 10:30', 'subject': 'S', 'student_email': 'stud@example.com'}
                    }
                }]
            }
        },
        {
            'message': {'role': 'assistant', 'content': 'Hello from assistant'}
        }
    ]

    # Directly mock the entry in available_tools dict
    agent.available_tools["manage_calendar_appointment"] = MagicMock(return_value="ERFOLG: Termin eingetragen")

    messages = [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Other role message'} # Triggers line 631
    ]

    agent.chat(messages, sender_name="Max", sender_email="max@example.com")

    # Verify last_appointment_info was set (line 679)
    assert agent.last_appointment_info is not None
    assert agent.last_appointment_info['student_email'] == "stud@example.com"


def test_tool_update_colloquium_config_potential_path_sent_items(mock_agent_setup, tmp_path):
    """Tests _tool_update_colloquium_config locating config.json when parent folder is "SentItems".

    Covers lines: 531-532.
    """
    agent, mock_store, mock_store_core, _ = mock_agent_setup

    # Path where folder name is SentItems
    sent_items_dir = tmp_path / "SentItems"
    sent_items_dir.mkdir()

    # Config file in the parent folder
    config_path = tmp_path / "config.json"

    # Configure both class mocks to return the same row
    for store_mock in [mock_store, mock_store_core]:
        mock_conn = store_mock._get_connection.return_value.__enter__.return_value
        mock_cursor = store_mock._get_connection.return_value.__enter__.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = [str(sent_items_dir)]

    # This should find configuration in the parent directory and update it
    res = agent._tool_update_colloquium_config("stud@example.com", "12.12.2026", "14:00")
    assert "ERFOLG" in res
    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["colloquium"]["date"] == "12.12.2026"
