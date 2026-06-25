import sys
from unittest.mock import MagicMock

# Simple mocking for all heavy dependencies
m = MagicMock()
sys.modules['numpy'] = m
sys.modules['sklearn'] = m
sys.modules['sklearn.ensemble'] = MagicMock()
sys.modules['sklearn.feature_extraction'] = MagicMock()
sys.modules['sklearn.feature_extraction.text'] = MagicMock()
sys.modules['sklearn.metrics'] = MagicMock()
sys.modules['sklearn.metrics.pairwise'] = MagicMock()
sys.modules['sklearn.model_selection'] = MagicMock()
sys.modules['sklearn.preprocessing'] = MagicMock()
sys.modules['extract_msg'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torch.nn'] = MagicMock()
sys.modules['torch.utils'] = MagicMock()
sys.modules['torch.utils.data'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['qdrant_client'] = MagicMock()
sys.modules['rank_bm25'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()
sys.modules['ollama'] = MagicMock()
sys.modules['xgboost'] = MagicMock()

import pytest
from unittest.mock import patch
from pathlib import Path
from mcp_university.classifier.controller import EmailController

@pytest.fixture
def controller():
    with patch("mcp_university.classifier.controller.get_config"), \
         patch("mcp_university.classifier.controller.Summarizer"), \
         patch("mcp_university.classifier.controller.PersonProfiler"), \
         patch("mcp_university.classifier.controller.Agent"):
        return EmailController()

def test_extract_honorific_preference(controller):
    # Test Du
    assert controller._extract_honorific_preference("Bevorzugte Anrede: Du") == "Du"
    assert controller._extract_honorific_preference("Man duzt sich mit dieser Person.") == "Du"
    assert controller._extract_honorific_preference("Anrede: Du") == "Du"

    # Test Sie (default)
    assert controller._extract_honorific_preference("Bevorzugte Anrede: Sie") == "Sie"
    assert controller._extract_honorific_preference(None) == "Sie"
    assert controller._extract_honorific_preference("") == "Sie"
    assert controller._extract_honorific_preference("Random profile text") == "Sie"

def test_detect_language_german(controller):
    controller.summarizer.client.chat.return_value = {"message": {"content": "German"}}
    assert controller._detect_language("Dies ist eine deutsche E-Mail.") == "German"

def test_detect_language_english(controller):
    controller.summarizer.client.chat.return_value = {"message": {"content": "English"}}
    assert controller._detect_language("This is an English email.") == "English"

def test_salutation_logic_german_sie(controller):
    controller.mail_parser.parse = MagicMock(return_value="Inhalt")
    controller._detect_language = MagicMock(return_value="German")
    controller._extract_honorific_preference = MagicMock(return_value="Sie")
    controller.summarizer.determine_gender = MagicMock(return_value="Herr")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))

    email_data = {"lastname": "Mustermann", "class": "Other"}
    controller.execute_action(0, Path("test.msg"), email_data)

    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Anrede: Guten Tag Herr Mustermann" in add_ctx
    assert kwargs["detected_language"] == "German"
    assert kwargs["honorific"] == "Sie"

def test_salutation_logic_english_du(controller):
    controller.mail_parser.parse = MagicMock(return_value="Content")
    controller._detect_language = MagicMock(return_value="English")
    controller._extract_honorific_preference = MagicMock(return_value="Du")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))

    email_data = {"lastname": "Mustermann", "class": "Other"}
    with patch("mcp_university.classifier.sort_emails.extract_firstname", return_value="Max"):
        controller.execute_action(0, Path("test.msg"), email_data)

    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Anrede: Hi Max" in add_ctx
    assert kwargs["detected_language"] == "English"
    assert kwargs["honorific"] == "Du"

def test_salutation_logic_english_sie(controller):
    controller.mail_parser.parse = MagicMock(return_value="Content")
    controller._detect_language = MagicMock(return_value="English")
    controller._extract_honorific_preference = MagicMock(return_value="Sie")
    controller.summarizer.determine_gender = MagicMock(return_value="Herr")
    controller.generate_reply = MagicMock(return_value=("Sub", "Text", False))

    email_data = {"lastname": "Mustermann", "class": "Other"}
    controller.execute_action(0, Path("test.msg"), email_data)

    args, kwargs = controller.generate_reply.call_args
    add_ctx = args[5]
    assert "Anrede: Dear Mr. Mustermann" in add_ctx
    assert kwargs["detected_language"] == "English"
    assert kwargs["honorific"] == "Sie"
