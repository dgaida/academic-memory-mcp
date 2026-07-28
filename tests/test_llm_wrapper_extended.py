"""Tests for test_llm_wrapper_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
import os
import sys
import importlib
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper

@pytest.fixture
def mock_cfg_llm():
    """Test fixture to mock LLM configuration."""
    with patch('mcp_university.utils.llm_client_wrapper.get_config') as mock_get:
        cfg = MagicMock()
        cfg.llm.model = "m"
        cfg.llm.base_url = "http://b"
        cfg.llm.temperature = 0.7
        cfg.llm.num_ctx = 4096
        cfg.llm.num_predict = 100
        mock_get.return_value = cfg
        yield cfg

def test_llm_wrapper_openai_success(mock_cfg_llm):
    """Test successful cloud provider call using openai."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True), \
         patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:
        
        mock_inst = mock_client_cls.return_value
        mock_inst.chat_completion.return_value = "Cloud Response"
        
        wrapper = LLMClientWrapper(provider="openai", api_key="sk-123")
        assert wrapper.provider == "openai"
        assert os.environ.get("OPENAI_API_KEY") == "sk-123"
        
        res = wrapper.chat([{"role": "user", "content": "Hi"}], system_prompt="Sys")
        assert res["message"]["content"] == "Cloud Response"

def test_llm_wrapper_openai_fail_fallback(mock_cfg_llm):
    """Test fallback to ollama when cloud initialization fails."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True), \
         patch('mcp_university.utils.llm_client_wrapper.LLMClient', side_effect=Exception("Init fail")), \
         patch('ollama.Client'):
        
        wrapper = LLMClientWrapper(provider="openai")
        assert wrapper.provider == "ollama"

def test_llm_wrapper_unsupported_fallback(mock_cfg_llm):
    """Test fallback to ollama when provider is unknown."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True), \
         patch('ollama.Client'):
        wrapper = LLMClientWrapper(provider="unknown")
        assert wrapper.provider == "ollama"

def test_llm_wrapper_cloud_chat_error(mock_cfg_llm):
    """Test exception safety in cloud chat method."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True), \
         patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:
        
        mock_inst = mock_client_cls.return_value
        mock_inst.chat_completion.side_effect = Exception("Chat fail")
        
        wrapper = LLMClientWrapper(provider="openai")
        res = wrapper.chat([{"role": "user", "content": "Hi"}])
        assert "Error: Chat fail" in res["message"]["content"]

def test_llm_wrapper_openai_tools_success(mock_cfg_llm):
    """Test tool calling with cloud provider."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True), \
         patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:

        mock_inst = mock_client_cls.return_value
        mock_inst.chat_completion_with_tools.return_value = {
            "content": "Thinking...",
            "tool_calls": [{"id": "1", "function": {"name": "test_tool", "arguments": "{}"}}]
        }

        wrapper = LLMClientWrapper(provider="openai")
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        res = wrapper.chat([{"role": "user", "content": "Call tool"}], tools=tools)

        assert res["message"]["content"] == "Thinking..."
        assert res["message"]["tool_calls"][0]["function"]["name"] == "test_tool"
        mock_inst.chat_completion_with_tools.assert_called_once()

def test_llm_wrapper_no_llm_client_module_fallback(mock_cfg_llm):
    """Test behavior when llm_client is not installed."""
    # Temporarily hide llm_client
    with patch.dict('sys.modules', {'llm_client': None}), patch('ollama.Client'):
        # Force reload of llm_client_wrapper to trigger HAS_LLM_CLIENT = False (lines 16-17)
        module_name = 'mcp_university.utils.llm_client_wrapper'
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])

        # Instantiate LLMClientWrapper with provider="openai"
        # Since HAS_LLM_CLIENT is False, it should fallback to ollama (lines 88-91)
        wrapper = LLMClientWrapper(provider="openai")
        assert wrapper.provider == "ollama"

    # Restore module state
    importlib.reload(sys.modules['mcp_university.utils.llm_client_wrapper'])

def test_llm_wrapper_no_provider_available(mock_cfg_llm):
    """Test that chat returns a placeholder error when no provider is available."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', False):
        # We also manually manipulate HAS_LLM_CLIENT to ensure the fallback in chat triggers line 154
        wrapper = LLMClientWrapper(provider="openai")
        # Ensure provider is set to anything other than "ollama"
        wrapper.provider = "unsupported_or_none"
        res = wrapper.chat([{"role": "user", "content": "Hi"}])
        assert res["message"]["content"] == "No provider available"
