"""Tests für die intelligente Terminbuchung und Konfliktprüfung."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from email_classifier.controller import EmailController
from mcp_university.agent.engine import Agent

@pytest.fixture
def temp_data_setup(tmp_path):
    """Erstellt ein temporäres Verzeichnis mit Kalenderdateien."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    appointments_file = data_dir / "appointments.md"
    appointments_content = """# Kalender Privat
| Start | Betreff | Teilnehmer |
| --- | --- | --- |
| 2026-07-21 10:00 | Team Meeting | Arbeit |
| 2026-07-21 14:00 | Blocker Besprechung | Privat |
| 2026-07-22 15:00 | Klausuraufsicht | Arbeit |
"""
    appointments_file.write_text(appointments_content, encoding="utf-8")

    free_slots_file = data_dir / "free_slots.md"
    free_slots_content = """# Freie Slots
* Mo, 2026-07-20 13:30-14:00
* Di, 2026-07-21 11:00-11:30
* Mi, 2026-07-22 10:00-10:30
"""
    free_slots_file.write_text(free_slots_content, encoding="utf-8")

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    return data_dir, config_dir

@pytest.fixture
def mock_controller_deps(temp_data_setup):
    """Mocks dependencies for EmailController."""
    data_dir, config_dir = temp_data_setup

    with patch('email_classifier.controller.get_config') as mock_get_config, \
         patch('email_classifier.controller.Summarizer'), \
         patch('email_classifier.controller.PersonProfiler'), \
         patch('email_classifier.controller.Agent') as mock_agent_class, \
         patch('email_classifier.controller.MailParser') as mock_parser_class:

        mock_cfg = MagicMock()
        mock_cfg.config_dir = config_dir
        mock_cfg.data_dir = data_dir
        mock_cfg.calendar.appointment_slots_path = "data/free_slots.md"
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.base_url = "http://test"
        mock_cfg.user.emails = ["prof@th-koeln.de"]
        mock_get_config.return_value = mock_cfg

        mock_agent = mock_agent_class.return_value
        mock_agent.last_appointment_info = None
        mock_agent.last_tool_error = None

        mock_parser = mock_parser_class.return_value

        yield mock_cfg, mock_agent, mock_parser

def test_intelligent_appointment_free_slot(mock_controller_deps, temp_data_setup):
    """Testet den Fall, dass der gewünschte Termin frei ist und gebucht werden kann."""
    mock_cfg, mock_agent, mock_parser = mock_controller_deps
    controller = EmailController()

    # Mocking incoming email with proposed time: Mi, 2026-07-22 10:00
    mock_parser.parse.return_value = "Ich lade Sie ein für Mittwoch, den 22.07.2026 um 10:00 Uhr."
    mock_parser.extract_latest_message.return_value = "Ich lade Sie ein für Mittwoch, den 22.07.2026 um 10:00 Uhr."

    mock_agent.chat.return_value = "APPOINTMENT_BOOKED"
    mock_agent.last_appointment_info = {"start_time": "2026-07-22 10:00"}

    mail_path = Path("test.msg")
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="Some Skill Content"):

        subject, reply, attach = controller.generate_reply(
            mail_path,
            action_idx=0 # Option 1 (runs Step 1 now!)
        )

    assert subject == "APPOINTMENT_BOOKED"
    assert "2026-07-22 10:00" in reply

def test_intelligent_appointment_conflict(mock_controller_deps, temp_data_setup):
    """Testet den Fall, dass der Termin belegt ist und Alternativen aus free_slots vorgeschlagen werden."""
    mock_cfg, mock_agent, mock_parser = mock_controller_deps
    controller = EmailController()

    # Mocking incoming email with proposed time: Di, 2026-07-21 10:00 (Conflict with Team Meeting!)
    mock_parser.parse.return_value = "Passt Dienstag, 21.07.2026 um 10:00 Uhr?"
    mock_parser.extract_latest_message.return_value = "Passt Dienstag, 21.07.2026 um 10:00 Uhr?"

    # The agent cannot book, so it suggests alternative slots
    suggested_reply = "Leider bin ich am Dienstag um 10:00 Uhr belegt (Team Meeting). Alternativ kann ich anbieten:\n- Di, 21.07.2026 11:00-11:30"
    mock_agent.chat.return_value = "BETREFF: Terminverschiebung\nTEXT:\n" + suggested_reply

    mail_path = Path("test.msg")
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.read_text', return_value="Some Skill Content"):

        subject, reply, attach = controller.generate_reply(
            mail_path,
            action_idx=0
        )

    assert "Terminverschiebung" in subject or subject != "APPOINTMENT_BOOKED"
    assert "belegt" in reply or "Team Meeting" in reply
    assert "Alternativ" in reply

def test_agent_tool_get_appointment_slots(temp_data_setup):
    """Prüft, ob das Agenten-Tool die freien Slots aus der richtigen Datei einliest."""
    data_dir, config_dir = temp_data_setup

    with patch('mcp_university.agent.engine.get_config') as mock_get_config, \
         patch('mcp_university.agent.engine.LLMClientWrapper'), \
         patch('mcp_university.agent.engine.ParserFactory'), \
         patch('mcp_university.agent.engine.MetadataStore'), \
         patch('mcp_university.agent.engine.SearchIndex'):

        mock_cfg = MagicMock()
        mock_cfg.config_dir = config_dir
        mock_cfg.data_dir = data_dir
        mock_cfg.calendar.appointment_slots_path = str(data_dir / "free_slots.md")
        mock_get_config.return_value = mock_cfg

        agent = Agent(model="test", base_url="test")
        agent.cfg = mock_cfg

        slots = agent._tool_get_appointment_slots()
        assert "2026-07-20 13:30-14:00" in slots
        assert "2026-07-21 11:00-11:30" in slots
