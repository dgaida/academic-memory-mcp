"""Tests for conftest.py."""
import pytest
import sys
import types
from unittest.mock import MagicMock, patch

def mock_package(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

# Global mocks for non-existent libraries
if "win32com" not in sys.modules:
    mock_win32 = mock_package("win32com")
    mock_win32_client = mock_package("win32com.client")
    mock_win32.client = mock_win32_client
    mock_win32_client.Dispatch = MagicMock()

if "ollama" not in sys.modules:
    mock_ollama = mock_package("ollama")
    mock_ollama.Client = MagicMock()

if "xgboost" not in sys.modules:
    mock_package("xgboost")

if "sentence_transformers" not in sys.modules:
    mock_package("sentence_transformers")
    mock_package("sentence_transformers.models")

@pytest.fixture
def mock_llm_client_wrapper():
    """Fixture to mock LLMClientWrapper across all tests."""
    instance = MagicMock()
    instance.model = "test-model"
    instance.chat = MagicMock()
    instance.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Default mock response', 'tool_calls': None}
    }

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
