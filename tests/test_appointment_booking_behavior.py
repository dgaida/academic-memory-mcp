"""Tests für das Buchungsverhalten von Terminen im EmailController."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Tuple
from mcp_university.classifier.controller import EmailController

@pytest.fixture
def mock_controller_deps() -> Tuple[MagicMock, MagicMock, MagicMock]:
    """Mockt Controller-Abhängigkeiten.

    Yields:
        Tupel aus (Config, Agent, Parser).
    """
    with patch('mcp_university.classifier.controller.get_config') as mock_get_config,           patch('mcp_university.classifier.controller.Summarizer'),           patch('mcp_university.classifier.controller.PersonProfiler'),           patch('mcp_university.classifier.controller.Agent') as mock_agent_class,           patch('mcp_university.classifier.controller.MailParser') as mock_parser_class:

        mock_cfg = MagicMock()
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_get_config.return_value = mock_cfg

        mock_agent = mock_agent_class.return_value
        mock_agent.last_appointment_info = None

        mock_parser = mock_parser_class.return_value

        yield mock_cfg, mock_agent, mock_parser

def test_generate_reply_triggers_appointment_tool(mock_controller_deps: Tuple[MagicMock, MagicMock, MagicMock]) -> None:
    """Verifiziert, dass generate_reply das Termin-Tool für eine Bestätigung aufruft.

    Args:
        mock_controller_deps: Gemockte Abhängigkeiten.
    """
    _, mock_agent, mock_parser = mock_controller_deps

    controller = EmailController()

    mock_parser.parse.return_value = "Ich lade ein am 8. Juli 2026 13:30 – 14:30 Uhr"
    mock_parser.extract_latest_message.return_value = "Ich lade ein am 8. Juli 2026 13:30 – 14:30 Uhr"

    mock_agent.chat.return_value = "APPOINTMENT_BOOKED"
    mock_agent.last_appointment_info = {"start_time": "2026-07-08 13:30"}

    mail_path = Path("test.msg")
    with patch('pathlib.Path.exists', return_value=True),           patch('pathlib.Path.read_text', return_value="Some Skill Content"):

        subject, reply, attach = controller.generate_reply(
            mail_path,
            action_idx=2
        )

    assert subject == "APPOINTMENT_BOOKED"
    assert "2026-07-08 13:30" in reply

    _, kwargs = mock_agent.chat.call_args
    prompt = kwargs['messages'][0]['content']
    assert "ERZWUNGENE AKTION: Diese E-Mail bestätigt einen Termin. Du MUSST ZWINGEND manage_calendar_appointment aufrufen." in prompt
    assert "VERBOTE:" in prompt
