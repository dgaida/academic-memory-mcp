"""Tests to boost coverage of mcp_university/mcp_server/tool_server.py."""

import json
from datetime import timedelta
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.mcp_server.tool_server import create_tool_server


@pytest.fixture
def mcp_context():
    """Initializes FastMCP server with mocked components for tests."""
    with patch('mcp_university.mcp_server.tool_server.MetadataStore') as mock_store_class, \
         patch('mcp_university.mcp_server.tool_server.SearchIndex') as mock_index_class, \
         patch('mcp_university.mcp_server.tool_server.ParserFactory') as mock_parser_factory_class, \
         patch('mcp_university.mcp_server.tool_server.get_config') as mock_get_config:

        mock_config = MagicMock()
        mock_config.sqlite_path = ":memory:"
        mock_config.qdrant_path = "/tmp/qdrant"
        mock_config.embeddings.model = "test-model"
        mock_config.data_dir = Path("/tmp/data")
        mock_config.user.email = "me@example.com"
        mock_get_config.return_value = mock_config

        server = create_tool_server()

        yield {
            'server': server,
            'store': mock_store_class.return_value,
            'index': mock_index_class.return_value,
            'parser_factory': mock_parser_factory_class.return_value
        }


def get_tool_by_name(mcp_server, name):
    """Finds a tool in FastMCP provider by name."""
    for comp in mcp_server.local_provider._components.values():
        if comp.name == name:
            return comp
    return None


def test_search_documents_no_results(mcp_context):
    """Test search_documents when no results are found."""
    comp = get_tool_by_name(mcp_context['server'], "search_documents")
    search_tool = comp.fn
    index = mcp_context['index']

    index.search.return_value = []
    result = search_tool("any query")
    assert "Keine relevanten Dokumente" in result


def test_get_student_info_not_found(mcp_context):
    """Test get_student_info when student does not exist."""
    comp = get_tool_by_name(mcp_context['server'], "get_student_info")
    student_tool = comp.fn
    store = mcp_context['store']

    mock_conn = store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    result = student_tool("Unknown Student")
    assert "Kein Student mit dem Namen" in result


def test_get_appointment_slots_missing_file(mcp_context):
    """Test get_appointment_slots when the file does not exist."""
    comp = get_tool_by_name(mcp_context['server'], "get_appointment_slots")
    slots_tool = comp.fn

    with patch("mcp_university.mcp_server.tool_server.Path.exists", return_value=False):
        result = slots_tool()
        assert "nicht vorhanden" in result


def test_get_appointment_slots_read_exception(mcp_context):
    """Test get_appointment_slots when file reading throws an exception."""
    comp = get_tool_by_name(mcp_context['server'], "get_appointment_slots")
    slots_tool = comp.fn

    with patch("mcp_university.mcp_server.tool_server.Path.exists", return_value=True), \
         patch("mcp_university.mcp_server.tool_server.Path.read_text", side_effect=IOError("Permission denied")):
        result = slots_tool()
        assert "Fehler beim Lesen der freien Slots" in result


def test_manage_calendar_appointment_import_error(mcp_context):
    """Test manage_calendar_appointment when win32com is not available."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": None, "win32com.client": None}):
        result = calendar_tool("2030-10-01 10:00", "2030-10-01 11:00", "Meeting", "test@student.com")
        assert "pywin32 ist nicht installiert" in result


def test_manage_calendar_appointment_colloquium_duration_adjust(mcp_context):
    """Test manage_calendar_appointment adjusts colloquium duration to 60 mins if < 60 mins."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_ns.Accounts.Count = 1
        mock_ns.Accounts.Item.return_value = mock_account

        mock_store = mock_account.DeliveryStore
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders.Count = 1
        mock_folder = MagicMock()
        mock_folder.Name = "Kalender (Nur dieser Computer)"
        mock_root.Folders.Item.return_value = mock_folder

        mock_appointment = mock_folder.Items.Add.return_value

        # Call tool with duration of 30 mins, but is_colloquium=True
        # It should adjust the duration
        result = calendar_tool("2030-10-01 10:00", "2030-10-01 10:30", "Colloquium", "test@student.com", is_colloquium=True)
        assert "ERFOLG" in result


def test_manage_calendar_appointment_default_folder_fallback_and_calendar_not_found(mcp_context):
    """Test default calendar folder fallback and calendar not found scenarios."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_ns.Accounts.Count = 1
        mock_ns.Accounts.Item.return_value = mock_account

        mock_store = mock_account.DeliveryStore
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders.Count = 1

        # 1. No folders match, but GetDefaultFolder(9) raises exception or works
        mock_root.Folders.Item.return_value = MagicMock(Name="Other Folder")
        mock_store.GetDefaultFolder.side_effect = Exception("No default folder")

        result = calendar_tool("2030-10-01 10:00", "2030-10-01 11:00", "Meeting", "test@student.com")
        assert "nicht gefunden" in result


def test_manage_calendar_appointment_invalid_times(mcp_context):
    """Test manage_calendar_appointment returns error if end_time <= start_time."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_ns.Accounts.Count = 1
        mock_ns.Accounts.Item.return_value = mock_account

        mock_store = mock_account.DeliveryStore
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders.Count = 1
        mock_folder = MagicMock()
        mock_folder.Name = "Kalender (Nur dieser Computer)"
        mock_root.Folders.Item.return_value = mock_folder

        result = calendar_tool("2030-10-01 11:00", "2030-10-01 10:00", "Meeting", "test@student.com")
        assert "muss nach dem Beginn" in result


def test_manage_calendar_appointment_update_colloquium_config_exception(mcp_context, caplog):
    """Test update_colloquium_config exception during manage_calendar_appointment colloquium flow."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        mock_outlook = win32com.client.Dispatch.return_value
        mock_ns = mock_outlook.GetNamespace.return_value

        mock_account = MagicMock()
        mock_account.SmtpAddress = "me@example.com"
        mock_ns.Accounts.Count = 1
        mock_ns.Accounts.Item.return_value = mock_account

        mock_store = mock_account.DeliveryStore
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders.Count = 1
        mock_folder = MagicMock()
        mock_folder.Name = "Kalender (Nur dieser Computer)"
        mock_root.Folders.Item.return_value = mock_folder

        mock_appointment = mock_folder.Items.Add.return_value

        # Making update_colloquium_config call raise an exception inside the try-catch of manage_calendar_appointment
        # by patching datetime or overriding strftime behavior to raise error!
        with patch("mcp_university.mcp_server.tool_server.datetime") as mock_datetime:
            mock_dt = MagicMock()
            mock_datetime.strptime.return_value = mock_dt
            mock_dt.replace.return_value = mock_dt
            # Support subtraction so duration comparison works
            mock_dt.__sub__.return_value = timedelta(minutes=60)
            mock_dt.__le__.return_value = False
            # Raise exception on strftime
            mock_dt.strftime.side_effect = Exception("Strftime failure")

            with caplog.at_level("ERROR"):
                result = calendar_tool("2030-10-01 10:00", "2030-10-01 11:00", "Meeting", "test@student.com", is_colloquium=True)
                assert "ERFOLG" in result
                assert "Fehler beim automatischen Update" in caplog.text


def test_manage_calendar_appointment_general_exception(mcp_context):
    """Test general exceptions during manage_calendar_appointment."""
    comp = get_tool_by_name(mcp_context['server'], "manage_calendar_appointment")
    calendar_tool = comp.fn

    with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        win32com.client.Dispatch.side_effect = Exception("System error")

        result = calendar_tool("2030-10-01 10:00", "2030-10-01 11:00", "Meeting", "test@student.com")
        assert "Fehler bei der Kalender-Verarbeitung" in result


def test_save_email_attachments_missing_file(mcp_context):
    """Test save_email_attachments when file does not exist."""
    comp = get_tool_by_name(mcp_context['server'], "save_email_attachments")
    save_tool = comp.fn

    with patch("pathlib.Path.exists", return_value=False):
        result = save_tool("nonexistent_mail.msg")
        assert "nicht gefunden" in result


def test_save_email_attachments_no_attachments(mcp_context, tmp_path):
    """Test save_email_attachments when no attachments exist."""
    comp = get_tool_by_name(mcp_context['server'], "save_email_attachments")
    save_tool = comp.fn

    email_path = tmp_path / "level1" / "level2" / "email.msg"

    def mock_exists_impl(path_obj):
        """Mock exists returning True for email.msg and False for level1."""
        if path_obj.name == "email.msg":
            return True
        if path_obj.name == "level1":
            return False
        return False

    with patch("pathlib.Path.exists", side_effect=mock_exists_impl, autospec=True), \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("mcp_university.parser.mail_parser.MailParser") as mock_parser_class:

        mock_parser = mock_parser_class.return_value
        mock_parser.save_attachments.return_value = []

        result = save_tool(str(email_path))
        assert "Keine Anhänge" in result
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_save_email_attachments_general_exception(mcp_context):
    """Test save_email_attachments when a general exception is raised."""
    comp = get_tool_by_name(mcp_context['server'], "save_email_attachments")
    save_tool = comp.fn

    with patch("pathlib.Path.exists", side_effect=Exception("Disk failure")):
        result = save_tool("mail.msg")
        assert "Fehler beim Speichern der Anhänge" in result


def test_create_colloquium_config_nonexistent_parent_dir(mcp_context, tmp_path):
    """Test create_colloquium_config when the target parent directory does not exist yet."""
    comp = get_tool_by_name(mcp_context['server'], "create_colloquium_config")
    create_config_tool = comp.fn

    email_path = tmp_path / "mails" / "subdir" / "test.msg"
    # Target parent is emails/mails/ (two parent levels up)

    result = create_config_tool(str(email_path), "thesis.pdf")
    assert "ERFOLG" in result
    config_file = tmp_path / "mails" / "config.json"
    assert config_file.exists()

    # Try calling it again when config.json exists to verify PDF update logic
    result_update = create_config_tool(str(email_path), "new_thesis.pdf")
    assert "ERFOLG" in result_update
    assert "new_thesis.pdf" in config_file.read_text()


def test_create_colloquium_config_general_exception(mcp_context):
    """Test create_colloquium_config when general exception occurs."""
    comp = get_tool_by_name(mcp_context['server'], "create_colloquium_config")
    create_config_tool = comp.fn

    with patch("pathlib.Path.exists", side_effect=Exception("Disk failure")):
        result = create_config_tool("mail.msg", "thesis.pdf")
        assert "Fehler beim Erstellen der Konfiguration" in result


def test_update_colloquium_config_missing_student(mcp_context):
    """Test update_colloquium_config when student is not in the database."""
    comp = get_tool_by_name(mcp_context['server'], "update_colloquium_config")
    update_config_tool = comp.fn
    store = mcp_context['store']

    mock_conn = store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = None

    result = update_config_tool("missing@student.com", "2030-10-01", "10:00")
    assert "Kein Ordner für Student" in result


def test_update_colloquium_config_potential_path(mcp_context, tmp_path):
    """Test update_colloquium_config searches parent path if config.json not in student folder."""
    comp = get_tool_by_name(mcp_context['server'], "update_colloquium_config")
    update_config_tool = comp.fn
    store = mcp_context['store']

    student_folder = tmp_path / "student_dir" / "Inbox"
    student_folder.mkdir(parents=True)

    # config.json sits in parent folder (student_dir)
    config_file = tmp_path / "student_dir" / "config.json"
    config_file.write_text('{"colloquium": {"date": "01.01.2020", "time": "12:00"}}')

    mock_conn = store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (str(student_folder),)

    result = update_config_tool("student@student.com", "15.10.2030", "14:30")
    assert "Kolloquiumstermin in" in result
    assert "15.10.2030" in config_file.read_text()


def test_update_colloquium_config_fallback_creation(mcp_context, tmp_path):
    """Test update_colloquium_config creates a config.json if it doesn't exist."""
    comp = get_tool_by_name(mcp_context['server'], "update_colloquium_config")
    update_config_tool = comp.fn
    store = mcp_context['store']

    student_folder = tmp_path / "student_dir" / "SentItems"
    student_folder.mkdir(parents=True)

    mock_conn = store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (str(student_folder),)

    # Call it to trigger fallback config creation since config.json is missing
    result = update_config_tool("student@student.com", "15.10.2030", "14:30")
    assert "ERFOLG" in result
    config_file = tmp_path / "student_dir" / "config.json"
    assert config_file.exists()
    config_data = json.loads(config_file.read_text())
    assert config_data["colloquium"]["date"] == "15.10.2030"
    assert config_data["colloquium"]["time"] == "14:30"


def test_update_colloquium_config_general_exception(mcp_context):
    """Test update_colloquium_config general exceptions."""
    comp = get_tool_by_name(mcp_context['server'], "update_colloquium_config")
    update_config_tool = comp.fn
    store = mcp_context['store']

    store._get_connection.side_effect = Exception("DB failure")
    result = update_config_tool("student@student.com", "15.10.2030", "14:30")
    assert "Fehler beim Aktualisieren der Konfiguration" in result
