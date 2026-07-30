"""Engine zur Erstellung und Verwaltung des Wissensgraphen."""
import logging
import json
from typing import List, Dict, Any, Optional
from mcp_university.metadata.store import MetadataStore
from mcp_university.summarizer.engine import Summarizer
from mcp_university.config import get_config, OntologyConfig

logger = logging.getLogger(__name__)

class KnowledgeGraphEngine:
    """Extrahiert Entitäten und Beziehungen aus Zusammenfassungen für den Wissensgraphen."""

    def __init__(self, store: MetadataStore, summarizer: Summarizer, ontology: Optional[OntologyConfig] = None) -> None:
        """Initialisiert die KnowledgeGraphEngine.

        Args:
            store (MetadataStore): Metadatenspeicher für den Graphen.
            summarizer (Summarizer): LLM Summarizer für Extraktion.
            ontology (Optional[OntologyConfig]): Ontologie-Konfiguration.
        """
        self.store = store
        self.summarizer = summarizer
        self.ontology = ontology or get_config().ontology

    def process_summary(self, summary_content: str, user_node_id: int) -> Dict[str, List[str]]:
        """Analysiert eine Zusammenfassung und aktualisiert den Graphen.

        Args:
            summary_content (str): Der Text der Zusammenfassung (.emails_summary.md).
            user_node_id (int): Die ID des Benutzer-Knotens (Zentrum).

        Returns:
            Dict[str, List[str]]: Zusammenfassung der Änderungen (neue/aktualisierte Knoten/Kanten).
        """
        changes = {"new_nodes": [], "updated_nodes": [], "new_edges": [], "updated_edges": []}
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

            # Alias-Auflösung
            canonical_source = self.store.resolve_canonical_name(source_name, source_type)
            canonical_target = self.store.resolve_canonical_name(target_name, target_type)

            source_id, s_new = self.store.upsert_node(canonical_source, source_type)
            if s_new:
                changes["new_nodes"].append(f"{canonical_source} ({source_type})")
            else:
                changes["updated_nodes"].append(canonical_source)

            target_id, t_new = self.store.upsert_node(canonical_target, target_type)
            if t_new:
                changes["new_nodes"].append(f"{canonical_target} ({target_type})")
            else:
                changes["updated_nodes"].append(canonical_target)

            # Kanten-Prioritäten prüfen (Ersetzung)
            should_add = self._handle_edge_priorities(source_id, target_id, relation)
            if not should_add:
                continue

            edge_id, e_new = self.store.upsert_edge(source_id, target_id, relation, properties)
            edge_desc = f"{canonical_source} --[{relation}]--> {canonical_target}"
            if e_new:
                changes["new_edges"].append(edge_desc)
            else:
                changes["updated_edges"].append(edge_desc)

        # Dubletten entfernen
        for key in changes:
            changes[key] = list(set(changes[key]))

        return changes

    def _handle_edge_priorities(self, source_id: int, target_id: int, new_relation: str) -> bool:
        """Prüft Kanten-Prioritäten und löscht ggf. unterlegene Kanten.

        Args:
            source_id (int): Startknoten.
            target_id (int): Zielknoten.
            new_relation (str): Die neue Beziehung.

        Returns:
            bool: Ob die neue Kante hinzugefügt werden soll.
        """
        if not self.ontology.edge_priorities:
            return True

        for category, priority_list in self.ontology.edge_priorities.items():
            if new_relation not in priority_list:
                continue

            new_priority = priority_list.index(new_relation)
            existing_edges = self.store.get_edges_between_nodes(source_id, target_id)

            for edge in existing_edges:
                rel = edge["relation_type"]
                if rel in priority_list:
                    old_priority = priority_list.index(rel)
                    if new_priority >= old_priority:
                        # Neue Kante hat höhere oder gleiche Priorität -> alte löschen
                        # (Gleiche Priorität wird durch upsert_edge sowieso aktualisiert, aber
                        #  hier löschen wir sie explizit, falls es ein anderer Name ist aber in derselben Liste)
                        # Hinweis: upsert_edge nutzt (source_id, target_id, relation_type) als UNIQUE.
                        # Wenn relation_type unterschiedlich ist, gäbe es sonst zwei Kanten.
                        if rel != new_relation:
                            self.store.delete_edge(source_id, target_id, rel)
                            logger.info(f"Kante '{rel}' durch '{new_relation}' ersetzt.")
                    else:
                        # Bestehende Kante hat höhere Priorität -> neue ignorieren
                        logger.info(f"Kante '{new_relation}' ignoriert, da '{rel}' höhere Priorität hat.")
                        return False
        return True

    def _extract_triplets(self, content: str) -> List[Dict[str, Any]]:
        """Nutzt das LLM, um Triplets aus dem Inhalt zu extrahieren."""
        node_types_str = ", ".join(self.ontology.node_types)
        edge_types_str = ", ".join(self.ontology.edge_types)

        system_prompt = f"""Du bist ein Experte für Wissensextraktion. Deine Aufgabe ist es, Informationen aus E-Mail-Zusammenfassungen in ein strukturiertes Format (Triplets) zu überführen.

Nutze NUR die folgenden Knotentypen und Beziehungstypen. Erfinde keine neuen Typen.

Knotentypen: {node_types_str}.
Beziehungstypen: {edge_types_str}.

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


def build_knowledge_graph(cfg: Any, store: Any, summarizer: Any, graph_engine: Any) -> None:
    """Baut den Wissensgraphen basierend auf den vorhandenen Zusammenfassungen auf.

    Args:
        cfg: Systemkonfiguration.
        store: Metadaten-Speicher.
        summarizer: Engine für Zusammenfassungen.
        graph_engine: Wissensgraph-Engine.
    """
    from pathlib import Path
    import yaml

    # User-Knoten sicherstellen
    user_node_id, _ = store.upsert_node(cfg.user.name, "Person", {"email": cfg.user.email, "role": ["User"]})
    print(f"Benutzer-Knoten initialisiert: {cfg.user.name}")

    # classifier_paths.yaml laden
    paths_file = cfg.config_dir / "classifier_paths.yaml"
    if not paths_file.exists():
        paths_file = cfg.config_dir / "classifier_paths.yaml.example"

    if not paths_file.exists():
        print("Fehler: classifier_paths.yaml nicht gefunden.")
        return

    with open(paths_file, "r", encoding="utf-8") as f:
        paths_data = yaml.safe_load(f)

    class_paths = paths_data.get("class_paths", {})

    for class_name, base_path_str in class_paths.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            continue

        print(f"Verarbeite Klasse: {class_name}")
        for summary_file in base_path.rglob(".emails_summary.md"):
            print(f"  Analysiere {summary_file}")
            content = summary_file.read_text(encoding='utf-8')
            changes = graph_engine.process_summary(content, user_node_id)
            if any(changes.values()):
                print(f"    Änderungen aus {summary_file.name}:")
                if changes['new_nodes']:
                    print(f"      Neue Knoten: {', '.join(changes['new_nodes'])}")
                if changes['new_edges']:
                    print("      Neue Beziehungen:")
                    for edge in changes['new_edges']:
                        print(f"        - {edge}")

        for summary_file in base_path.rglob(".*_summary.md"):
            if summary_file.name == ".emails_summary.md":
                continue
            print(f"  Analysiere Ordner-Zusammenfassung {summary_file}")
            content = summary_file.read_text(encoding='utf-8')
            changes = graph_engine.process_summary(content, user_node_id)
            if any(changes.values()):
                print(f"    Änderungen aus {summary_file.name}:")
                if changes['new_nodes']:
                    print(f"      Neue Knoten: {', '.join(changes['new_nodes'])}")
                if changes['new_edges']:
                    print("      Neue Beziehungen:")
                    for edge in changes['new_edges']:
                        print(f"        - {edge}")

    print("Wissensgraph erfolgreich aktualisiert.")
