"""Agenten-Logik für das MCP University System."""
import logging
from typing import List, Dict, Any
from ..config import get_config
from ..metadata.store import MetadataStore
from ..metadata.kg_store import KnowledgeGraphStore
from ..retrieval.index import SearchIndex
from ..parser.factory import ParserFactory

logger = logging.getLogger(__name__)

class Agent:
    """Basis-Agent für Aufgaben in der Universität."""

    def __init__(self, model: str, base_url: str, **kwargs) -> None:
        """Initialisiert den Agenten."""
        self.model = model
        self.base_url = base_url
        self.cfg = get_config()
        self.student_store = MetadataStore(self.cfg.metadata_db_path)
        self.th_store = KnowledgeGraphStore(self.cfg.kg_db_path)
        self.store = self.student_store
        self.index = SearchIndex(str(self.cfg.qdrant_path), self.cfg.embeddings.model, store=self.store)
        self.parser_factory = ParserFactory(self.cfg.data_dir / "cache")
        self.last_appointment_info = None
        self.available_tools = {}

    def chat(self, messages: List[Dict[str, Any]], system_prompt: str = "", **kwargs) -> str:
        """Führt eine Konversation mit dem Agenten."""
        from ..utils.llm_client_wrapper import LLMClientWrapper
        client = LLMClientWrapper()

        while True:
            response = client.chat(messages, system_prompt=system_prompt)
            msg = response["message"]

            if "tool_calls" in msg and msg["tool_calls"]:
                messages.append(msg)
                for tool_call in msg["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]
                    if func_name in self.available_tools:
                        result = self.available_tools[func_name](**args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": func_name,
                            "content": str(result)
                        })
                continue

            return msg.get("content", "")

    def _tool_read_file(self, path: str) -> str:
        """Liest eine Datei ein."""
        from pathlib import Path
        p = Path(path)
        if p.exists():
            return self.parser_factory.parse(p)
        return "Datei nicht gefunden."
