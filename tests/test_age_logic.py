import sys
import os
from unittest.mock import MagicMock, patch

# Mock all heavy third-party libraries at module level
mock_modules = [
    'torch', 'sentence_transformers', 'xgboost', 'qdrant_client',
    'rank_bm25', 'extract_msg', 'sklearn', 'sklearn.metrics',
    'sklearn.metrics.pairwise', 'sklearn.ensemble',
    'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
    'sklearn.preprocessing', 'pydantic', 'yaml', 'dotenv', 'transformers', 'ollama'
]
for module in mock_modules:
    if module not in sys.modules:
        sys.modules[module] = MagicMock()

if 'torch' in sys.modules:
    sys.modules['torch'].Tensor = type('Tensor', (), {})

# Mock internal submodules
sys.modules['mcp_university.agent'] = MagicMock()
sys.modules['mcp_university.agent.mcp_agent'] = MagicMock()
sys.modules['mcp_university.agent.engine'] = MagicMock()
sys.modules['mcp_university.classifier.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.engine'] = MagicMock()
sys.modules['mcp_university.summarizer.profiler'] = MagicMock()
sys.modules['mcp_university.utils.llm_client_wrapper'] = MagicMock()

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta

@patch('mcp_university.classifier.controller.get_config')
@patch('mcp_university.classifier.controller.MailParser')
@patch('mcp_university.classifier.controller.PersonProfiler')
@patch('mcp_university.classifier.controller.Summarizer')
@patch('mcp_university.classifier.controller.Agent')
def test_age_months_suggested_action(mock_agent, mock_summarizer, mock_profiler, mock_parser_cls, mock_config, tmp_path):
    from mcp_university.classifier.controller import EmailController
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    mock_parser = mock_parser_cls.return_value
    mock_parser.get_email_date.return_value = datetime.now() - timedelta(days=185)

    # Create dummy mail file
    mail_dir = source_dir / "dir1"
    mail_dir.mkdir(parents=True)
    mail_path = mail_dir / "mail.msg"
    mail_path.write_text("dummy")

    controller = EmailController()
    controller.parse_report = MagicMock(return_value=[{
        "lastname": "StudentOld",
        "class": "ClassA",
        "semester": "WS2023",
        "path": str(mail_path),
        "folder": "Inbox"
    }])

    emails = controller.process_all_emails(source_dir, age_months=3)
    assert emails[0]["suggested_action"] == 3

@patch('mcp_university.classifier.controller.get_config')
@patch('mcp_university.classifier.controller.MailParser')
@patch('mcp_university.classifier.controller.PersonProfiler')
@patch('mcp_university.classifier.controller.Summarizer')
@patch('mcp_university.classifier.controller.Agent')
def test_sent_items_suggested_action(mock_agent, mock_summarizer, mock_profiler, mock_parser_cls, mock_config, tmp_path):
    from mcp_university.classifier.controller import EmailController
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    mock_parser = mock_parser_cls.return_value
    mock_parser.get_email_date.return_value = datetime.now()

    mail_dir = source_dir / "dir1"
    mail_dir.mkdir(parents=True)
    mail_path = mail_dir / "mail.msg"
    mail_path.write_text("dummy")

    controller = EmailController()
    controller.parse_report = MagicMock(return_value=[{
        "lastname": "StudentSent",
        "class": "ClassA",
        "semester": "WS2023",
        "path": str(mail_path),
        "folder": "SentItems"
    }])

    emails = controller.process_all_emails(source_dir)
    assert emails[0]["suggested_action"] == 3
