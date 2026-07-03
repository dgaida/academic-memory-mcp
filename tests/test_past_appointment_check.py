import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from email_classifier.controller import EmailController
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

@pytest.fixture
def mock_controller_deps():
    with patch('email_classifier.controller.get_config') as mock_get_config,          patch('email_classifier.controller.Summarizer'),          patch('email_classifier.controller.PersonProfiler'),          patch('email_classifier.controller.Agent') as mock_agent_class,          patch('email_classifier.controller.MailParser') as mock_parser_class:

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_get_config.return_value = mock_cfg

        mock_agent = mock_agent_class.return_value
        mock_agent.last_appointment_info = None
        mock_agent.last_tool_error = None

        mock_parser = mock_parser_class.return_value

        yield mock_cfg, mock_agent, mock_parser

def test_generate_reply_past_appointment_archived(mock_controller_deps):
    """Verifies that generate_reply archives emails with past appointments."""
    mock_cfg, mock_agent, mock_parser = mock_controller_deps

    controller = EmailController()

    # Mock mail parsing
    mock_parser.parse.return_value = "Ich lade ein am 8. Juli 2020 13:30 – 14:30 Uhr"
    mock_parser.extract_latest_message.return_value = "Ich lade ein am 8. Juli 2020 13:30 – 14:30 Uhr"

    # Mock LLM behavior: agent returns APPOINTMENT_BOOKED but tool failed with "Vergangenheit"
    mock_agent.chat.return_value = "APPOINTMENT_BOOKED"
    mock_agent.last_appointment_info = None
    mock_agent.last_tool_error = "Fehler: Der Termin liegt in der Vergangenheit und wird daher nicht angelegt."

    mail_path = Path("test.msg")
    with patch('pathlib.Path.exists', return_value=True),          patch('pathlib.Path.read_text', return_value="Some Skill Content"):

        subject, reply, attach = controller.generate_reply(
            mail_path,
            action_idx=2 # 3) Termin im Kalender anlegen
        )

    assert subject == "NO_REPLY_NEEDED"
    assert reply == "Archiviert (Termin in Vergangenheit)"
    assert attach is False

def test_manage_calendar_appointment_past_check():
    """Unit test for the past date check in the agent engine."""
    from mcp_university.agent.engine import Agent

    with patch('mcp_university.agent.engine.LLMClientWrapper'),          patch('mcp_university.agent.engine.ParserFactory'),          patch('mcp_university.agent.engine.MetadataStore'),          patch('mcp_university.agent.engine.SearchIndex'):

        # We need to mock win32com.client which is used inside manage_calendar_appointment
        import sys
        sys.modules['win32com'] = MagicMock()
        sys.modules['win32com.client'] = MagicMock()

        agent = Agent(model="test", base_url="test")
        agent.cfg = MagicMock()
        agent.cfg.calendar.account = "test@example.com"

        # Test with a date in the past
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        result = agent._tool_manage_calendar_appointment(
            subject="Test",
            start_time=past_date,
            end_time=(datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
            student_email="student@test.com"
        )

        assert "Vergangenheit" in result
