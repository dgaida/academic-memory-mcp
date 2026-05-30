"""Agent, der Tools über einen MCP-Server aufruft."""
import logging
from typing import List, Dict, Optional
from ..config import get_config
from ..utils.llm_client_wrapper import LLMClientWrapper
from ..utils.anonymizer import Anonymizer

logger = logging.getLogger(__name__)

class MCPAgent:
    """Agent, der Tool-Calling mittels Cloud/Lokal LLM und MCP-Tools unterstützt."""

    def __init__(self, model: str = None, base_url: str = None, use_cloud: bool = False, cloud_provider: str = "openai", cloud_model: str = "gpt-4o", api_key: str = None):
        self.cfg = get_config()
        self.model = model or self.cfg.llm.model
        self.base_url = str(base_url or self.cfg.llm.base_url)
        self.last_appointment_info = None

        self.use_cloud = use_cloud
        if self.use_cloud:
            self.client = LLMClientWrapper(provider=cloud_provider, model=cloud_model, api_key=api_key)
            self.anonymizer = Anonymizer(model=self.model, base_url=self.base_url)
        else:
            self.client = LLMClientWrapper(provider="ollama", model=self.model, base_url=self.base_url)
            self.anonymizer = None

        from ..mcp_server.tool_server import create_tool_server
        self.mcp_instance = create_tool_server()

        self.available_tools = {}
        for component in self.mcp_instance.local_provider._components.values():
            if hasattr(component, "fn") and hasattr(component, "name"):
                self.available_tools[component.name] = component.fn

        self.tools_definition = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Liest den Inhalt einer Datei ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Sucht in Dokumenten.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_info",
                    "description": "Liefert Studentendaten.",
                    "parameters": {
                        "type": "object",
                        "properties": {"student_name": {"type": "string"}},
                        "required": ["student_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_appointment_slots",
                    "description": "Liest freie Slots.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_calendar_appointment",
                    "description": "Trägt Kalendertermin ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "subject": {"type": "string"},
                            "student_email": {"type": "string"},
                            "original_mail_date": {"type": "string"}
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            }
        ]

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None, sender_name: str = None, sender_email: str = None) -> str:
        """Chat-Interaktion mit MCP Tools und optionaler Anonymisierung."""
        self.last_appointment_info = None

        processed_messages = []
        if self.use_cloud and self.anonymizer and sender_name and sender_email:
            for msg in messages:
                if msg['role'] == 'user':
                    anon_content = self.anonymizer.anonymize(msg['content'], sender_name, sender_email)
                    processed_messages.append({'role': 'user', 'content': anon_content})
                else:
                    processed_messages.append(msg)
            if system_prompt:
                system_prompt = self.anonymizer.anonymize(system_prompt, sender_name, sender_email)
        else:
            processed_messages = messages

        all_messages = processed_messages.copy()
        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.chat(messages=all_messages, system_prompt=system_prompt, tools=self.tools_definition)
            message = response.get('message', {})

            if self.use_cloud and self.anonymizer:
                if message.get('content'):
                    message['content'] = self.anonymizer.deanonymize_text(message['content'])
                if message.get('tool_calls'):
                    for tc in message['tool_calls']:
                        tc['function']['arguments'] = self.anonymizer.deanonymize_args(tc['function'].get('arguments', {}))

            all_messages.append(message)
            if not message.get('tool_calls'):
                return message.get('content', "")

            for tool_call in message['tool_calls']:
                fn_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})
                if fn_name in self.available_tools:
                    try:
                        res = self.available_tools[fn_name](**args)
                        if fn_name == "manage_calendar_appointment" and "ERFOLG" in str(res):
                            self.last_appointment_info = args
                    except Exception as e:
                        res = f"Fehler: {e}"
                else:
                    res = "Tool nicht gefunden."

                if self.use_cloud and self.anonymizer:
                    for placeholder, original in self.anonymizer.mapping.items():
                        res = str(res).replace(original, placeholder)

                all_messages.append({'role': 'tool', 'content': str(res), 'tool_call_id': tool_call.get('id')})

        return "Fehler: Maximale Iterationen erreicht."
