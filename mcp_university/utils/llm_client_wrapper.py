"""Wrapper for LLM calls supporting local and cloud providers."""

import logging
import os
from typing import Any, Dict, List

import ollama

from ..config import get_config

logger = logging.getLogger(__name__)

try:
    from llm_client import LLMClient
    HAS_LLM_CLIENT = True
except ImportError:
    HAS_LLM_CLIENT = False


class LLMClientWrapper:
    """Synchronous wrapper for LLM calls, supporting both local Ollama and cloud providers."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = None,
        base_url: str = None,
        api_key: str = None,
    ) -> None:
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
            # Map common names to llm-client names
            api_choice_map = {
                "openai": "openai",
                "groq": "groq",
                "gemini": "gemini",
                "google": "gemini",
            }
            api_choice = api_choice_map.get(self.provider)
            if api_choice:
                # Set environment variable for the API key if provided to ensure LLMClient picks it up
                if self.api_key:
                    env_key_map = {
                        "openai": "OPENAI_API_KEY",
                        "groq": "GROQ_API_KEY",
                        "gemini": "GEMINI_API_KEY",
                    }
                    env_key = env_key_map.get(api_choice)
                    if env_key:
                        os.environ[env_key] = self.api_key

                try:
                    self.client = LLMClient(api_choice=api_choice, llm=self.model, temperature=self.cfg.llm.temperature)
                except Exception as e:
                    logger.error(f"Failed to initialize LLMClient for {api_choice}: {e}")
                    logger.warning("Falling back to Ollama.")
                    self.provider = "ollama"
                    self.client = ollama.Client(host=str(self.base_url))
            else:
                logger.warning(
                    f"Provider {provider} not supported by LLMClient. Falling back to Ollama."
                )
                self.provider = "ollama"
                self.client = ollama.Client(host=str(self.base_url))
        else:
            self.provider = "ollama"
            self.client = ollama.Client(host=str(self.base_url))

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        tools: List[Dict] = None,
    ) -> Dict[str, Any]:
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
                all_messages.append({"role": "system", "content": system_prompt})
            all_messages.extend(messages)

            # Ollama's client.chat is synchronous
            response = self.client.chat(
                model=self.model, messages=all_messages, tools=tools, options={"temperature": self.cfg.llm.temperature}
            )
            return response

        elif HAS_LLM_CLIENT:
            chat_messages = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                # Ensure we only pass role and content as expected by llm-client
                chat_messages.append(
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                )

            try:
                # LLMClient.chat_completion is synchronous
                content = self.client.chat_completion(chat_messages)
                return {
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": None,
                    }
                }
            except Exception as e:
                logger.error(f"Cloud LLM error: {e}")
                return {
                    "message": {
                        "role": "assistant",
                        "content": f"Error: {e}",
                        "tool_calls": None,
                    }
                }

        return {
            "message": {
                "role": "assistant",
                "content": "No provider available",
                "tool_calls": None,
            }
        }
