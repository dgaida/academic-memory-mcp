import pytest
import sys
from unittest.mock import MagicMock, patch

# Global mocks for non-existent libraries
mock_win32 = MagicMock()
sys.modules["win32com"] = mock_win32
sys.modules["win32com.client"] = mock_win32.client
sys.modules["ollama"] = MagicMock()

# Mock xgboost if not available
try:
    import importlib.util
    if importlib.util.find_spec("xgboost") is None:
        sys.modules["xgboost"] = MagicMock()
except Exception:
    sys.modules["xgboost"] = MagicMock()

# Mock sentence_transformers if not available
try:
    if importlib.util.find_spec("sentence_transformers") is None:
        sys.modules["sentence_transformers"] = MagicMock()
except Exception:
    sys.modules["sentence_transformers"] = MagicMock()

@pytest.fixture
def mock_llm_client_wrapper():
    """Fixture to mock LLMClientWrapper across all tests."""
    instance = MagicMock()
    instance.model = "test-model"
    instance.chat = MagicMock()
    instance.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Default mock response', 'tool_calls': None}
    }

    # We patch it in all locations to be safe
    targets = [
        'mcp_university.utils.llm_client_wrapper.LLMClientWrapper',
        'mcp_university.summarizer.engine.LLMClientWrapper',
        'mcp_university.agent.engine.LLMClientWrapper',
        'mcp_university.agent.mcp_agent.LLMClientWrapper',
        'mcp_university.utils.anonymizer.LLMClientWrapper',
    ]

    active_patches = []
    for target in targets:
        try:
            p = patch(target)
            mock_class = p.start()
            mock_class.return_value = instance
            active_patches.append(p)
        except Exception:
            pass

    yield instance

    for p in active_patches:
        p.stop()

@pytest.fixture(autouse=True)
def mock_outlook_dependencies():
    """Fixture to mock Outlook-related dependencies for all tests."""
    with patch('mcp_university.utils.outlook.is_outlook_open', return_value=True),          patch('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True):
        yield
