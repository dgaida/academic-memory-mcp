"""Modul für den Agenten mit Tool-Calling-Unterstützung."""
import logging
from typing import List, Dict, Callable
from pathlib import Path
import ollama

from ..config import get_config
from ..parser.factory import ParserFactory
from ..retrieval.index import SearchIndex
from ..metadata.store import MetadataStore

logger = logging.getLogger(__name__)

class Agent:
    """Agent, der Tool-Calling mittels Ollama unterstützt."""

    def __init__(self, model: str = None, base_url: str = None):
        """Initialisiert den Agenten.

        Args:
            model (str, optional): Name des Ollama-Modells.
            base_url (str, optional): Basis-URL des Ollama-Servers.
        """
        cfg = get_config()
        self.model = model or cfg.llm.model
        self.base_url = base_url or cfg.llm.base_url
        self.client = ollama.Client(host=self.base_url)

        self.parser_factory = ParserFactory(cfg.data_dir / "cache")
        self.store = MetadataStore(cfg.sqlite_path)
        self.index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=self.store)

        self.available_tools: Dict[str, Callable] = {
            "read_file": self._tool_read_file,
            "search_documents": self._tool_search_documents,
            "get_student_info": self._tool_get_student_info
        }

        self.tools_definition = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Liest den Inhalt einer Datei (PDF, DOCX, MD, TXT, MSG) ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Der Pfad zur Datei."
                            }
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
                            "query": {
                                "type": "string",
                                "description": "Die Suchanfrage."
                            }
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
                            "student_name": {
                                "type": "string",
                                "description": "Name oder Teilname des Studenten."
                            }
                        },
                        "required": ["student_name"]
                    }
                }
            }
        ]

    def _tool_read_file(self, path: str) -> str:
        """Liest eine Datei ein."""
        p = Path(path)
        if not p.exists():
            return f"Fehler: Datei {path} nicht gefunden."
        content = self.parser_factory.parse(p)
        return content or "Fehler: Datei konnte nicht gelesen werden oder ist leer."

    def _tool_search_documents(self, query: str) -> str:
        """Sucht im Index."""
        results = self.index.search(query, top_k=3)
        if not results:
            return "Keine relevanten Dokumente gefunden."

        output = ""
        for res in results:
            output += f"--- {res['filename']} (Score: {res['score']:.2f}) ---\n{res['content']}\n\n"
        return output

    def _tool_get_student_info(self, student_name: str) -> str:
        """Holt Studentendaten."""
        with self.store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, f.path as folder_path FROM students s
                LEFT JOIN folders f ON s.folder_id = f.id
                WHERE s.name LIKE ?
            ''', (f"%{student_name}%",))
            student = cursor.fetchone()
            if not student:
                return f"Kein Student mit dem Namen {student_name} gefunden."

            # (id, name, email, topic, status, folder_id, folder_path)
            context = f"Student: {student[1]}\nEmail: {student[2]}\nThema: {student[3]}\nStatus: {student[4]}\nOrdner: {student[6]}\n"
            return context

    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Führt eine Chat-Interaktion mit Tool-Calling-Loop durch.

        Args:
            messages: Liste der Chat-Nachrichten.
            system_prompt: Optionaler System-Prompt.

        Returns:
            str: Die finale Antwort des Agenten.
        """
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

            # Verarbeite Tool-Calls
            for tool_call in message['tool_calls']:
                function_name = tool_call['function']['name']
                args = tool_call['function'].get('arguments', {})

                logger.info(f"Agent ruft Tool auf: {function_name} mit {args}")

                if function_name in self.available_tools:
                    try:
                        tool_result = self.available_tools[function_name](**args)
                    except Exception as e:
                        tool_result = f"Fehler bei Tool-Ausführung: {e}"
                else:
                    tool_result = f"Tool {function_name} nicht verfügbar."

                all_messages.append({
                    'role': 'tool',
                    'content': str(tool_result),
                    'tool_call_id': tool_call.get('id') # Ollama supports this if present
                })

        return "Fehler: Maximale Anzahl an Iterationen erreicht."
