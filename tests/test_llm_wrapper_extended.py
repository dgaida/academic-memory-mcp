"""Tests for test_llm_wrapper_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
import os
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper

@pytest.fixture
def mock_cfg_llm():
    """Test function docstring."""
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
    """Test function docstring."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True),          patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:
        
        mock_inst = mock_client_cls.return_value
        mock_inst.chat_completion.return_value = "Cloud Response"
        
        wrapper = LLMClientWrapper(provider="openai", api_key="sk-123")
        assert wrapper.provider == "openai"
        assert os.environ.get("OPENAI_API_KEY") == "sk-123"
        
        res = wrapper.chat([{"role": "user", "content": "Hi"}], system_prompt="Sys")
        assert res["message"]["content"] == "Cloud Response"

def test_llm_wrapper_openai_fail_fallback(mock_cfg_llm):
    """Test function docstring."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True),          patch('mcp_university.utils.llm_client_wrapper.LLMClient', side_effect=Exception("Init fail")),          patch('ollama.Client'):
        
        wrapper = LLMClientWrapper(provider="openai")
        assert wrapper.provider == "ollama"

def test_llm_wrapper_unsupported_fallback(mock_cfg_llm):
    """Test function docstring."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True),          patch('ollama.Client'):
        wrapper = LLMClientWrapper(provider="unknown")
        assert wrapper.provider == "ollama"

def test_llm_wrapper_cloud_chat_error(mock_cfg_llm):
    """Test function docstring."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True),          patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:
        
        mock_inst = mock_client_cls.return_value
        mock_inst.chat_completion.side_effect = Exception("Chat fail")
        
        wrapper = LLMClientWrapper(provider="openai")
        res = wrapper.chat([{"role": "user", "content": "Hi"}])
        assert "Error: Chat fail" in res["message"]["content"]

def test_llm_wrapper_openai_tools_success(mock_cfg_llm):
    """Test tool calling with cloud provider."""
    with patch('mcp_university.utils.llm_client_wrapper.HAS_LLM_CLIENT', True),          patch('mcp_university.utils.llm_client_wrapper.LLMClient') as mock_client_cls:

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
