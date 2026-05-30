"""Wrapper for LLM calls supporting local and cloud providers."""
import logging
import ollama
import asyncio
from typing import List, Dict, Any
from ..config import get_config

logger = logging.getLogger(__name__)

try:
    from llm_client import LLMAPIClientFactory, LLMAPIClientType, LLMAPIClientConfig, ChatMessage, Role
    HAS_LLM_CLIENT = True
except ImportError:
    HAS_LLM_CLIENT = False

class LLMClientWrapper:
    """Synchronous wrapper for LLM calls, supporting both local Ollama and cloud providers."""

    def __init__(self, provider: str = "ollama", model: str = None, base_url: str = None, api_key: str = None):
        """Initializes the LLMClientWrapper.

        Args:
            provider (str): Name of the provider (ollama, openai, etc.). Defaults to "ollama".
            model (str, optional): Name of the LLM model. Defaults to None.
            base_url (str, optional): Base URL for the LLM API. Defaults to None.
            api_key (str, optional): API key for cloud providers. Defaults to None.
        """
        self.cfg = get_config()
        self.provider = provider.lower()
        self.model = model or self.cfg.llm.model
        self.base_url = base_url or self.cfg.llm.base_url
        self.api_key = api_key

        if self.provider == "ollama":
            self.client = ollama.Client(host=str(self.base_url))
        elif HAS_LLM_CLIENT:
            provider_map = {
                "openai": LLMAPIClientType.OPEN_AI,
                "anthropic": LLMAPIClientType.ANTHROPIC,
                "google": LLMAPIClientType.GOOGLE,
            }
            client_type = provider_map.get(self.provider)
            if client_type:
                config = LLMAPIClientConfig(api_key=self.api_key, model=self.model)
                self.client = LLMAPIClientFactory.get_chat_client(client_type, config)
            else:
                logger.warning(f"Provider {provider} not supported. Falling back to Ollama.")
                self.provider = "ollama"
                self.client = ollama.Client(host=str(self.base_url))
        else:
            self.provider = "ollama"
            self.client = ollama.Client(host=str(self.base_url))

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None, tools: List[Dict] = None) -> Dict[str, Any]:
        """Sends a chat request and returns a dict compatible with Ollama's response format.

        Args:
            messages (List[Dict[str, str]]): List of chat messages.
            system_prompt (str, optional): System prompt. Defaults to None.
            tools (List[Dict], optional): List of tool definitions. Defaults to None.

        Returns:
            Dict[str, Any]: Response dictionary with 'message' key.
        """
        if self.provider == "ollama":
            all_messages = []
            if system_prompt:
                all_messages.append({'role': 'system', 'content': system_prompt})
            all_messages.extend(messages)

            # Ollama's client.chat is synchronous
            response = self.client.chat(model=self.model, messages=all_messages, tools=tools)
            return response

        elif HAS_LLM_CLIENT:
            chat_messages = []
            if system_prompt:
                chat_messages.append(ChatMessage(role=Role.SYSTEM, content=system_prompt))
            for msg in messages:
                role = Role.USER if msg['role'] == 'user' else Role.ASSISTANT
                if msg["role"] == "system":
                    role = Role.SYSTEM
                chat_messages.append(ChatMessage(role=role, content=msg['content']))

            try:
                # llm-client is mostly async. We wrap it in a sync call.
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()

                async def _call():
                    """Internal async call."""
                    return await self.client.chat(chat_messages)

                resp = asyncio.run(_call())
                content = resp[0].content if resp else ""
                return {'message': {'role': 'assistant', 'content': content, 'tool_calls': None}}
            except Exception as e:
                logger.error(f"Cloud LLM error: {e}")
                return {'message': {'role': 'assistant', 'content': f"Error: {e}", 'tool_calls': None}}

        return {'message': {'role': 'assistant', 'content': "No provider available", 'tool_calls': None}}
