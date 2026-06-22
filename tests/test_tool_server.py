import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from mcp_university.mcp_server.tool_server import create_tool_server

@pytest.fixture
def mcp_context():
    with patch('mcp_university.mcp_server.tool_server.MetadataStore') as mock_store_class,          patch('mcp_university.mcp_server.tool_server.SearchIndex') as mock_index_class,          patch('mcp_university.mcp_server.tool_server.ParserFactory') as mock_parser_factory_class,          patch('mcp_university.mcp_server.tool_server.get_config') as mock_get_config:
        
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
    for comp in mcp_server.local_provider._components.values():
        if comp.name == name:
            return comp
    return None

def test_tool_registration(mcp_context):
    tools = mcp_context['server'].local_provider._components
    tool_names = [comp.name for comp in tools.values()]
    assert "read_file" in tool_names
    assert "search_documents" in tool_names
    assert "get_student_info" in tool_names
    assert "get_appointment_slots" in tool_names
    assert "manage_calendar_appointment" in tool_names
    assert "save_email_attachments" in tool_names

def test_tool_read_file(mcp_context):
    comp = get_tool_by_name(mcp_context['server'], "read_file")
    read_file_tool = comp.fn
    parser_factory = mcp_context['parser_factory']
    
    with patch("pathlib.Path.exists", return_value=True):
        parser_factory.parse.return_value = "content"
        assert read_file_tool("some_path") == "content"
            
    with patch("pathlib.Path.exists", return_value=False):
        assert "nicht gefunden" in read_file_tool("missing_path")

def test_tool_search_documents(mcp_context):
    comp = get_tool_by_name(mcp_context['server'], "search_documents")
    search_tool = comp.fn
    index = mcp_context['index']
            
    index.search.return_value = [{"filename": "doc1.pdf", "score": 0.9, "content": "found text"}]
    
    result = search_tool("query")
    assert "doc1.pdf" in result
    assert "found text" in result

def test_tool_get_student_info(mcp_context):
    comp = get_tool_by_name(mcp_context['server'], "get_student_info")
    student_tool = comp.fn
    store = mcp_context['store']
            
    mock_conn = store._get_connection.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    
    mock_cursor.fetchone.side_effect = [
        (1, "Max Mustermann", "max@smail.th-koeln.de", "Topic", "Active", "/path/to/folder"),
        ("Folder summary content",)
    ]
    
    result = student_tool("Max")
    assert "Max Mustermann" in result
    assert "Folder summary content" in result

def test_tool_get_appointment_slots(mcp_context):
    comp = get_tool_by_name(mcp_context['server'], "get_appointment_slots")
    slots_tool = comp.fn
            
    with patch("mcp_university.mcp_server.tool_server.Path") as mock_path:
        mock_file = mock_path.return_value
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "Slot 1: 10:00"
        
        assert slots_tool() == "Slot 1: 10:00"

def test_tool_manage_calendar_appointment(mcp_context):
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
        
        result = calendar_tool("2024-10-01 10:00", "2024-10-01 11:00", "Test Meeting", "student@example.com")
            
        assert "ERFOLG" in result
        assert mock_appointment.Save.called

def test_tool_save_email_attachments(mcp_context):
    comp = get_tool_by_name(mcp_context['server'], "save_email_attachments")
    save_tool = comp.fn
            
    with patch("mcp_university.parser.mail_parser.MailParser") as mock_parser_class:
        mock_parser = mock_parser_class.return_value
        mock_parser.save_attachments.return_value = [Path("file1.pdf")]
        
        with patch("pathlib.Path.exists", return_value=True):
            result = save_tool("mail.msg")
            assert "ERFOLG" in result
            assert "file1.pdf" in result
