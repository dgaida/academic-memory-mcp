"""Agent, der Tools über einen MCP-Server aufruft."""
import logging
from typing import List, Dict
from ..config import get_config
from ..utils.llm_client_wrapper import LLMClientWrapper
from ..utils.anonymizer import Anonymizer

logger = logging.getLogger(__name__)

class MCPAgent:
    """Agent, der Tool-Calling mittels Ollama und MCP-Tools unterstützt und optional Cloud-LLMs mit Anonymisierung nutzt."""

    def __init__(self, model: str = None, base_url: str = None, use_cloud: bool = False,
                 cloud_provider: str = "openai", cloud_model: str = "gpt-4o", api_key: str = None) -> None:
        """Initialisiert den MCPAgent.

        Args:
            model (str, optional): Name des lokalen Ollama-Modells. Defaults to None.
            base_url (str, optional): Basis-URL des Ollama-Servers. Defaults to None.
            use_cloud (bool): Ob ein Cloud-LLM genutzt werden soll. Defaults to False.
            cloud_provider (str): Name des Cloud-Providers. Defaults to "openai".
            cloud_model (str): Name des Cloud-Modells. Defaults to "gpt-4o".
            api_key (str, optional): API-Key für den Cloud-Provider. Defaults to None.
        """
        self.cfg = get_config()
        self.model = model or self.cfg.llm.model
        self.last_appointment_info = None
        self.last_tool_error = None
        self.base_url = str(base_url or self.cfg.llm.base_url)

        self.use_cloud = use_cloud
        if self.use_cloud:
            self.client = LLMClientWrapper(provider=cloud_provider, model=cloud_model, api_key=api_key)
            self.anonymizer = Anonymizer(model=self.model, base_url=self.base_url)
        else:
            self.client = LLMClientWrapper(provider="ollama", model=self.model, base_url=self.base_url)
            self.anonymizer = None

        from ..mcp_server.tool_server import create_tool_server
        self.mcp_instance = create_tool_server()

        # Tools aus MCP extrahieren
        self.available_tools = {}
        for component in self.mcp_instance.local_provider._components.values():
            if hasattr(component, "fn") and hasattr(component, "name"):
                self.available_tools[component.name] = component.fn

        self.tools_definition = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Liest den Inhalt einer Datei (PDF, DOCX, MD, TXT, MSG) ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Der Pfad zur Datei."}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Sucht in den indexierten Universitäts-Dokumenten nach Informationen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Die Suchanfrage."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_info",
                    "description": "Liefert Informationen und Kontext zu einem Studenten.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_name": {"type": "string", "description": "Name des Studenten."}
                        },
                        "required": ["student_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_appointment_slots",
                    "description": "Liest die aktuell verfügbaren freien Terminslots aus.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_calendar_appointment",
                    "description": "Trägt einen Kalendertermin ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string", "description": "Beginn (YYYY-MM-DD HH:MM)."},
                            "end_time": {"type": "string", "description": "Ende (YYYY-MM-DD HH:MM)."},
                            "subject": {"type": "string", "description": "Betreff."},
                            "student_email": {"type": "string", "description": "E-Mail."},
                            "original_mail_date": {"type": "string", "description": "Datum der studentischen Mail (DD.MM.YY)."},
                            "body": {"type": "string", "description": "Inhalt des Termins (z.B. Link zur E-Mail)."}
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_email_attachments",
                    "description": "Extrahiert Anhänge aus einer E-Mail und speichert sie im Elternordner.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_path": {"type": "string", "description": "Pfad zur E-Mail."}
                        },
                        "required": ["email_path"]
                    }
                }
            }
        ]

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None,
             sender_name: str = None, sender_email: str = None) -> str:
        """Chat-Interaktion mit MCP Tools und optionaler Anonymisierung.

        Args:
            messages (List[Dict[str, str]]): Liste der Chat-Nachrichten.
            system_prompt (str, optional): Optionaler System-Prompt. Defaults to None.
            sender_name (str, optional): Name des Absenders für Anonymisierung. Defaults to None.
            sender_email (str, optional): E-Mail des Absenders für Anonymisierung. Defaults to None.

        Returns:
            str: Die finale Antwort des Agenten.
        """
        self.last_appointment_info = None
        self.last_tool_error = None

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

        all_messages = []
        if system_prompt:
            all_messages.append({'role': 'system', 'content': system_prompt})
        all_messages.extend(processed_messages)

        max_iterations = 5
        for i in range(max_iterations):
            logger.debug(f"MCP Agent Iteration {i+1}/{max_iterations}")
            response = self.client.chat(
                messages=all_messages,
                tools=self.tools_definition
            )

            message = response.get('message', {})
            logger.debug(f"MCP Agent Antwort-Message: {message}")

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
                function_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})
                logger.info(f"MCP Agent ruft Tool auf: {function_name} mit {args}")

                if function_name in self.available_tools:
                    try:
                        tool_result = self.available_tools[function_name](**args)
                        logger.info(f"MCP Tool Ergebnis ({function_name}): {tool_result}")
                        if function_name == "manage_calendar_appointment" and "ERFOLG" in str(tool_result):
                            self.last_appointment_info = args
                    except Exception as e:
                        tool_result = f"Fehler bei MCP Tool-Ausführung: {e}"
                        logger.error(tool_result)
                        self.last_tool_error = tool_result
                else:
                    tool_result = f"MCP Tool {function_name} nicht verfügbar."
                    logger.warning(tool_result)

                if self.use_cloud and self.anonymizer:
                    for placeholder, original in self.anonymizer.mapping.items():
                        tool_result = str(tool_result).replace(original, placeholder)

                all_messages.append({
                    'role': 'tool',
                    'content': str(tool_result),
                    'tool_call_id': tool_call.get('id')
                })

        return "Fehler: Maximale Iterationen im MCP Agent erreicht."
