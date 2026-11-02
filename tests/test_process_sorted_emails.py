"""Tests für den EmailController."""
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Mock dependencies to avoid side effects during import/init
with patch('mcp_university.agent.engine.SearchIndex'),      patch('mcp_university.agent.engine.MetadataStore'),      patch('mcp_university.agent.engine.ParserFactory'),      patch('mcp_university.agent.mcp_agent.MCPAgent'):
    from email_classifier.controller import EmailController
from mcp_university.utils.outlook import create_outlook_draft

@patch('email_classifier.controller.MCPAgent')
@patch('email_classifier.controller.Agent')
def test_parse_sorted_report(mock_agent, mock_mcp_agent, tmp_path):
    """Prüft das Parsen des sortierten E-Mail Reports.

    Args:
        mock_agent: Mock für Agent.
        mock_mcp_agent: Mock für MCPAgent.
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    report = tmp_path / "sorted_emails.md"
    report.write_text("# Sortierte\n\n## Class\n| Semester | Nachname | Ordner | Datei |\n| --- | --- | --- | --- |\n| S | Name | Inbox | D:\\mail.msg |", encoding="utf-8")
    
    controller = EmailController()
    emails = controller.parse_report(report)
    assert len(emails) == 1

@patch("email_classifier.controller.MailParser")
@patch("email_classifier.controller.Agent")
@patch("email_classifier.controller.MCPAgent")
def test_generate_reply_appointment_booked(mock_mcp_agent, mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn ein Termin erfolgreich gebucht wurde.

    Args:
        mock_mcp_agent: Mock für die MCPAgent-Klasse.
        mock_agent_cls: Mock für die Agent-Klasse.
        mock_parser_cls: Mock für die MailParser-Klasse.
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    # Agent.chat returns a string
    mock_agent_cls.return_value.chat.return_value = "APPOINTMENT_BOOKED"
    mock_agent_cls.return_value.last_appointment_info = {"start_time": "2026-06-22 14:00"}
    mock_agent_cls.return_value.last_tool_error = None

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    _, reply, _ = controller.generate_reply(mail_path)
    assert "APPOINTMENT_BOOKED" in reply

@patch("email_classifier.controller.MailParser")
@patch("email_classifier.controller.Agent")
@patch("email_classifier.controller.MCPAgent")
def test_generate_reply_no_appointment_fallback(mock_mcp_agent, mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet den Fallback der Antwortgenerierung, wenn keine Terminterrelevanz vorliegt.

    Args:
        mock_mcp_agent: Mock für die MCPAgent-Klasse.
        mock_agent_cls: Mock für die Agent-Klasse.
        mock_parser_cls: Mock für die MailParser-Klasse.
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

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
            mock_cfg.return_value.user.email = "test@example.com"
            success = create_outlook_draft("S", "B")
            assert success is True

@patch("email_classifier.controller.MailParser")
@patch("email_classifier.controller.Agent")
@patch("email_classifier.controller.MCPAgent")
def test_generate_reply_no_reply_needed(mock_mcp_agent, mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet die Generierung einer Antwort, wenn keine Antwort erforderlich ist.

    Args:
        mock_mcp_agent: Mock für die MCPAgent-Klasse.
        mock_agent_cls: Mock für die Agent-Klasse.
        mock_parser_cls: Mock für die MailParser-Klasse.
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

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

@patch("email_classifier.controller.MailParser")
@patch("email_classifier.controller.Agent")
@patch("email_classifier.controller.MCPAgent")
def test_generate_reply_with_instructions(mock_mcp_agent, mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet, dass Hinweise und Regieanweisungen an den LLM Prompt weitergegeben werden.

    Args:
        mock_mcp_agent: Mock für MCPAgent.
        mock_agent_cls: Mock für Agent.
        mock_parser_cls: Mock für MailParser.
        tmp_path: Pytest Fixture für temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)
    mock_agent_cls.return_value.chat.side_effect = [
        "NO_APPOINTMENT_RELEVANCE",
        "NO_FINAL_SUBMISSION_RELEVANCE",
        "REPLY_NEEDED",
        "ANHANG: NEIN\nBETREFF: Betreff\nTEXT:\nAntworttext",
    ]

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    instructions = "Schlage ein paar Terminvorschläge per zoom vor und sei besonders freundlich."
    controller.generate_reply(mail_path, action_idx=0, instructions=instructions)

    call_args_list = mock_agent_cls.return_value.chat.call_args_list
    step2_call = call_args_list[-1]
    messages = step2_call[1]["messages"]
    user_prompt = messages[0]["content"]

    assert instructions in user_prompt
    assert "BESONDERE HINWEISE / REGIEANWEISUNGEN DES NUTZERS" in user_prompt
    assert "Beachte unbedingt die folgenden Regieanweisungen/Hinweise des Nutzers" in user_prompt

@patch("email_classifier.controller.MailParser")
@patch("email_classifier.controller.Agent")
@patch("email_classifier.controller.MCPAgent")
def test_execute_action_passes_instructions(mock_mcp_agent, mock_agent_cls, mock_parser_cls, tmp_path):
    """Testet, dass execute_action Hinweise an generate_reply weiterreicht.

    Args:
        mock_mcp_agent: Mock für MCPAgent.
        mock_agent_cls: Mock für Agent.
        mock_parser_cls: Mock für MailParser.
        tmp_path: Pytest Fixture für temporäres Verzeichnis.

    Returns:
        None
    """
    mock_parser = mock_parser_cls.return_value
    mock_parser.parse.return_value = "content"
    mock_parser.extract_latest_message.return_value = "content"

    controller = EmailController(debug=False)

    mail_path = tmp_path / "test.msg"
    mail_path.write_text("dummy")

    with patch.object(controller.profiler, "get_profile", return_value="Profile"), \
         patch.object(controller, "generate_reply", return_value=("Betreff", "Inhalt", False)) as mock_gen_reply, \
         patch("email_classifier.controller.create_outlook_draft", return_value=True):
        controller.execute_action(
            0,
            mail_path,
            {"lastname": "Mustermann", "instructions": "Stichpunkte einbinden"},
        )
        mock_gen_reply.assert_called_once()
        assert mock_gen_reply.call_args[1].get("instructions") == "Stichpunkte einbinden"

        mock_gen_reply.reset_mock()
        controller.execute_action(
            0,
            mail_path,
            {"lastname": "Mustermann"},
            instructions="Direkte Anweisung",
        )
        mock_gen_reply.assert_called_once()
        assert mock_gen_reply.call_args[1].get("instructions") == "Direkte Anweisung"
