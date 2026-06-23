import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock all heavy third-party libraries at the module level
sys.modules['torch'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['xgboost'] = MagicMock()
sys.modules['qdrant_client'] = MagicMock()
sys.modules['rank_bm25'] = MagicMock()
sys.modules['extract_msg'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()
sys.modules['sklearn.metrics.pairwise'] = MagicMock()
sys.modules['sklearn.ensemble'] = MagicMock()
sys.modules['sklearn.feature_extraction'] = MagicMock()
sys.modules['sklearn.feature_extraction.text'] = MagicMock()
sys.modules['sklearn.preprocessing'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['yaml'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Mock the entire agent submodule to avoid imports
sys.modules['mcp_university.agent'] = MagicMock()
sys.modules['mcp_university.agent.mcp_agent'] = MagicMock()
sys.modules['mcp_university.agent.engine'] = MagicMock()
sys.modules['mcp_university.classifier.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.profiler'] = MagicMock()
sys.modules['mcp_university.utils.llm_client_wrapper'] = MagicMock()

# Import the controller
# We need to mock get_config before importing if it's used at module level,
# but it's usually used inside functions/classes.
with patch('mcp_university.classifier.controller.get_config'), \
     patch('mcp_university.classifier.controller.MailParser'), \
     patch('mcp_university.classifier.controller.PersonProfiler'), \
     patch('mcp_university.classifier.controller.Summarizer'):
    from mcp_university.classifier.controller import EmailController
from mcp_university.utils.outlook import create_outlook_draft

def test_parse_sorted_report(tmp_path):
    """Prüft das Parsen des sortierten E-Mail Reports.

    Args:
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\n\n## Class\n- **S** | Name | Inbox: `D:\\mail.msg`", encoding="utf-8")
    with patch('mcp_university.classifier.controller.Agent'), \
         patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        # Mock get_config return value to avoid StopIteration if it's called multiple times
        mock_get_config.return_value = MagicMock()
        controller = EmailController()
        emails = controller.parse_report(report)
        assert len(emails) == 1

def test_processed_emails_report_generation(tmp_path):
    """Prüft die Generierung des processed_emails.md Berichts.

    Dieser Test verifiziert, dass die Methode write_processed_report eine Datei
    erstellt, die alle übergebenen Ergebnisse im korrekten Markdown-Format enthält.

    Args:
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    with patch('mcp_university.classifier.controller.Agent'), \
         patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController()
        results = [
            {"lastname": "Mustermann", "subject": "Frage", "status": "Beantwortet"},
            {"lastname": "Schmidt", "subject": "Termin", "status": "Archiviert"}
        ]

        controller.write_processed_report(tmp_path, results)

        report_file = tmp_path / "processed_emails.md"
        assert report_file.exists()

        content = report_file.read_text(encoding="utf-8")
        assert "# Verarbeitete E-Mails" in content
        assert "| Mustermann | Frage | Beantwortet |" in content
        assert "| Schmidt | Termin | Archiviert |" in content

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_appointment_booked(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    with patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController(debug=False)
        # Agent.chat returns a string
        mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"
        mock_agent_cls.return_value.last_appointment_info = {"start_time": "2026-06-22 14:00"}
        mock_agent_cls.return_value.last_tool_error = None

        mail_path = tmp_path / "test.msg"
        mail_path.write_text("dummy")

        _, reply, _ = controller.generate_reply(mail_path)
        assert "APPOINTMENT_BOOKED" in reply

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_no_appointment_fallback(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet den Fallback der Antwortgenerierung, wenn keine Terminterrelevanz vorliegt.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    with patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController(debug=False)
        # Agent.chat side effects
        mock_agent_cls.return_value.chat.side_effect = [
            "NO_APPOINTMENT_RELEVANCE",
            "NO_FINAL_SUBMISSION_RELEVANCE",
            "REPLY_NEEDED",
            "ANHANG: NEIN\nBETREFF: T\nTEXT:\nReply"
        ]

        mail_path = tmp_path / "test.msg"
        mail_path.write_text("dummy")

        _, reply, _ = controller.generate_reply(mail_path)
        assert reply == "Reply"

def test_create_outlook_draft_success():
    """Testet die erfolgreiche Erstellung eines Outlook-Entwurfs.

    Args:
        None

    Returns:
        None
    """
    with patch('win32com.client.Dispatch') as mock_dispatch:
        mock_outlook = mock_dispatch.return_value
        mock_namespace = mock_outlook.GetNamespace.return_value
        mock_store = MagicMock()
        mock_store.DisplayName = "test@example.com"
        mock_namespace.Stores = [mock_store]
        mock_root = mock_store.GetRootFolder.return_value
        mock_root.Folders = []

        mock_mail = MagicMock()
        mock_outlook.CreateItem.return_value = mock_mail

        with patch('mcp_university.utils.outlook.get_config') as mock_cfg:
            mock_cfg.return_value = MagicMock()
            mock_cfg.return_value.user.email = "test@example.com"
            success = create_outlook_draft("S", "B")
            assert success is True

@patch("mcp_university.classifier.controller.MailParser")
@patch("mcp_university.classifier.controller.Agent")
def test_generate_reply_no_reply_needed(mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn keine Antwort erforderlich ist.

    Args:
        mock_agent_cls (MagicMock): Mock für die Agent-Klasse.
        mock_parser_cls (MagicMock): Mock für die MailParser-Klasse.
        tmp_path (Path): Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    with patch('mcp_university.classifier.controller.get_config') as mock_get_config:
        mock_get_config.return_value = MagicMock()
        controller = EmailController(debug=False)
        mock_agent_cls.return_value.chat.side_effect = [
            "NO_APPOINTMENT_RELEVANCE",
            "NO_FINAL_SUBMISSION_RELEVANCE",
            "NO_REPLY_NEEDED|Reason"
        ]
        mail_path = tmp_path / "test.msg"
        mail_path.write_text("dummy")
        subject, _, _ = controller.generate_reply(mail_path)
        assert subject == "NO_REPLY_NEEDED"
