"""Agent, der Tools über einen MCP-Server aufruft."""
import logging
from typing import List, Dict
import ollama
from ..config import get_config

logger = logging.getLogger(__name__)

class MCPAgent:
    """Agent, der Tool-Calling mittels Ollama und MCP-Tools unterstützt."""

    def __init__(self, model: str = None, base_url: str = None):
        self.cfg = get_config()
        self.model = model or self.cfg.llm.model
        self.base_url = str(base_url or self.cfg.llm.base_url)
        self.client = ollama.Client(host=self.base_url)

        # In einer echten Umgebung würde man sich hier mit dem MCP Server verbinden
        # und die Tool-Definitionen dynamisch abrufen.
        # Da wir im selben Repo sind und die Tools statisch bekannt sind,
        # simulieren wir den MCP-Aufruf indem wir die Tool-Server-Logik einbinden
        # oder (für diese Aufgabe) die Tools manuell definieren, die im tool_server.py stehen.

        from ..mcp_server.tool_server import create_tool_server
        self.mcp_instance = create_tool_server()

        # Tools aus MCP extrahieren
        self.available_tools = {}
        self.tools_definition = []

        for tool in self.mcp_instance._tools:
            name = tool.name
            self.available_tools[name] = tool.callable

            # Konvertiere FastMCP Tool-Definition zu Ollama Format
            # Da FastMCP Docstrings und Typen nutzt, müssen wir sie parsen oder
            # (einfacher) wir nehmen an sie sind analog zum lokalen Agenten.

            # Wir nutzen hier die Definitionen aus dem tool_server.py
            # Da Ollama ein spezifisches Format braucht:

        # Hardcoded definitions for the MCP tools to ensure correctness with Ollama
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
                            "original_mail_date": {"type": "string", "description": "Datum der studentischen Mail (DD.MM.YY)."}
                        },
                        "required": ["start_time", "end_time", "subject", "student_email"]
                    }
                }
            }
        ]

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Analog zu Agent.chat, nutzt aber MCP Tools."""
        all_messages = []
        if system_prompt:
            all_messages.append({'role': 'system', 'content': system_prompt})
        all_messages.extend(messages)

        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.chat(
                model=self.model,
                messages=all_messages,
                tools=self.tools_definition
            )

            message = response.get('message', {})
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
                    except Exception as e:
                        tool_result = f"Fehler bei MCP Tool-Ausführung: {e}"
                else:
                    tool_result = f"MCP Tool {function_name} nicht verfügbar."

                all_messages.append({
                    'role': 'tool',
                    'content': str(tool_result),
                    'tool_call_id': tool_call.get('id')
                })

        return "Fehler: Maximale Iterationen im MCP Agent erreicht."
