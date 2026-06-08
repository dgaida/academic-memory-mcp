"""Engine zur Erstellung und Verwaltung des Wissensgraphen."""
import logging
import json
from typing import List, Dict, Any
from mcp_university.metadata.store import MetadataStore
from mcp_university.summarizer.engine import Summarizer

logger = logging.getLogger(__name__)

class KnowledgeGraphEngine:
    """Extrahiert Entitäten und Beziehungen aus Zusammenfassungen für den Wissensgraphen."""

    def __init__(self, store: MetadataStore, summarizer: Summarizer):
        self.store = store
        self.summarizer = summarizer

    def process_summary(self, summary_content: str, user_node_id: int):
        """Analysiert eine Zusammenfassung und aktualisiert den Graphen.

        Args:
            summary_content (str): Der Text der Zusammenfassung (.emails_summary.md).
            user_node_id (int): Die ID des Benutzer-Knotens (Zentrum).
        """
        triplets = self._extract_triplets(summary_content)
        for triplet in triplets:
            source_name = triplet.get("source")
            target_name = triplet.get("target")
            relation = triplet.get("relation")
            source_type = triplet.get("source_type", "Person")
            target_type = triplet.get("target_type", "Person")
            properties = triplet.get("properties", {})

            if not source_name or not target_name or not relation:
                continue

            # Falls source oder target der "User" ist (oder "ich", "mich", etc.), nutzen wir user_node_id
            # Das LLM sollte idealerweise schon die Namen kennen.

            source_id = self.store.upsert_node(source_name, source_type)
            target_id = self.store.upsert_node(target_name, target_type)

            self.store.upsert_edge(source_id, target_id, relation, properties)

    def _extract_triplets(self, content: str) -> List[Dict[str, Any]]:
        """Nutzt das LLM, um Triplets aus dem Inhalt zu extrahieren."""
        system_prompt = """Du bist ein Experte für Wissensextraktion. Deine Aufgabe ist es, Informationen aus E-Mail-Zusammenfassungen in ein strukturiertes Format (Triplets) zu überführen.
Knotentypen: Person, Modul, Unternehmen.
Beziehungstypen: lehrt, besucht, schreibt Bachelorarbeit, hat Bachelorarbeit angefragt, hat Bachelorarbeit abgeschlossen, schreibt Masterarbeit, hat Masterarbeit angefragt, hat Masterarbeit abgeschlossen, schreibt Projektarbeit, hat Projektarbeit angefragt, hat Projektarbeit abgeschlossen, hat Nachteilsausgleich beantragt, hat PO-Wechsel beantragt.
Knoten-Eigenschaften: Für Personen 'Rolle' (z.B. Professor, Studierender, Prüfungsausschussvorsitzender).

Antworte NUR mit einer JSON-Liste von Objekten mit den Schlüsseln: source, target, relation, source_type, target_type, properties.
"""
        user_prompt = f"""Extrahiere Triplets aus der folgenden Zusammenfassung:

{content}
"""
        response = self.summarizer._chat_request(system_prompt, user_prompt)
        if not response:
            return []

        try:
            # Versuche JSON zu finden, falls das LLM Text drumherum baut
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(response[start_idx:end_idx])
            return []
        except Exception as e:
            logger.error(f"Fehler beim Parsen der Triplets: {e}")
            return []
