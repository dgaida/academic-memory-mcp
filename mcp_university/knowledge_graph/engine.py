"""Engine zur Extraktion von Wissen aus Zusammenfassungen."""
import json
import logging
from typing import Dict, Any, Optional, List
from mcp_university.summarizer.engine import Summarizer
from mcp_university.config import OntologyConfig

logger = logging.getLogger(__name__)

class KnowledgeGraphEngine:
    """Extrahiert Entitäten und Beziehungen aus Texten."""

    def __init__(self, store: Any, summarizer: Summarizer, ontology: Optional[OntologyConfig] = None) -> None:
        """Initialisiert die Engine."""
        self.store = store
        self.summarizer = summarizer
        self.ontology = ontology

    def process_summary(self, content: str, user_node_id: int) -> Dict[str, List[str]]:
        """Verarbeitet eine Zusammenfassung."""
        ontology_info = ""
        if self.ontology:
            ontology_info = f"Knotentypen: {', '.join(self.ontology.node_types)}\nBeziehungstypen: {', '.join(self.ontology.edge_types)}\nNutze NUR die folgenden Knotentypen und Beziehungstypen."

        prompt = f"{ontology_info}\nExtrahiere Wissen als JSON-Liste von Triplets: {content}"

        try:
            response = self.summarizer._chat_request(prompt)
            triplets = json.loads(response)
        except Exception as e:
            logger.error(f"Extraktionsfehler: {e}")
            return {"new_nodes": [], "new_edges": []}

        new_nodes = []
        new_edges = []

        for t in triplets:
            source_type = t.get("source_type", "Person")
            target_type = t.get("target_type", "Modul")

            s_id, s_new = self.store.upsert_node(t["source"], source_type, t.get("properties", {}))
            if s_new:
                new_nodes.append(t["source"])

            t_id, t_new = self.store.upsert_node(t["target"], target_type, {})
            if t_new:
                new_nodes.append(t["target"])

            if self._should_upsert_edge(s_id, t_id, t["relation"]):
                _, e_new = self.store.upsert_edge(s_id, t_id, t["relation"], t.get("properties", {}))
                if e_new:
                    new_edges.append(f"{t['source']} --{t['relation']}--> {t['target']}")

        return {"new_nodes": new_nodes, "new_edges": new_edges}

    def _should_upsert_edge(self, source_id: int, target_id: int, relation: str) -> bool:
        """Prüft Prioritäten."""
        if not self.ontology or not self.ontology.edge_priorities:
            return True

        for priority_list in self.ontology.edge_priorities.values():
            if relation not in priority_list:
                continue

            current_prio = priority_list.index(relation)
            existing_edges = self.store.get_edges_between_nodes(source_id, target_id)

            for edge in existing_edges:
                if edge['relation_type'] in priority_list:
                    existing_prio = priority_list.index(edge['relation_type'])
                    if current_prio < existing_prio:
                        return False
                    self.store.delete_edge(source_id, target_id, edge['relation_type'])
        return True
