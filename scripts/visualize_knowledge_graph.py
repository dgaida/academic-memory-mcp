"""Skript zur interaktiven Visualisierung des Wissensgraphen mittels Pyvis.

Beispiele:
    # Gesamten Graphen anzeigen
    python scripts/visualize_knowledge_graph.py

    # Nach einem Knoten filtern (inkl. Eltern-Strukturen und Teilgraphen)
    python scripts/visualize_knowledge_graph.py --filter "Mustermann"

    # Nach mehreren Knoten filtern
    python scripts/visualize_knowledge_graph.py --filter "Mustermann" "Informatik"
"""
import sys
import argparse
from pathlib import Path
import networkx as nx
from pyvis.network import Network
import logging

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from mcp_university.config import get_config
from mcp_university.metadata.store import MetadataStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """Hauptfunktion zur Generierung der HTML-Visualisierung des Wissensgraphen.
    
    Liest alle Knoten und Kanten aus dem MetadataStore und erstellt eine
    interaktive Pyvis-Visualisierung.
    """
    parser = argparse.ArgumentParser(description="Visualisierung des Wissensgraphen.")
    parser.add_argument("--filter", type=str, nargs="+", help="Filtert den Graphen nach einem oder mehreren Knotennamen. Zeigt die Knoten, ihre Eltern-Strukturen (eingehende Kanten) und alle davon ausgehenden Teilgraphen.")
    args = parser.parse_args()

    config = get_config()
    store = MetadataStore(config.sqlite_path)

    nodes = store.get_all_nodes()
    edges = store.get_all_edges()

    if not nodes:
        logger.warning("Keine Knoten im Graphen gefunden.")
        return

    # Create NetworkX graph
    G = nx.MultiDiGraph()

    # Color mapping for node types
    type_colors = {
        "Person": "#97c2fc",      # Blue
        "Modul": "#ffff00",       # Yellow
        "Unternehmen": "#fb7e81", # Red
        "User": "#00ff00",        # Green
        "Fakultät": "#ffa500",     # Orange
        "Einrichtung": "#da70d6",  # Orchid
        "Institut": "#32cd32"      # LimeGreen
    }

    # Add nodes
    for node in nodes:
        node_id = node["id"]
        name = node["name"]
        node_type = node["type"]

        # Check if it's the user node based on config
        color = type_colors.get(node_type, "#97c2fc")
        if name == config.user.name:
            color = type_colors["User"]

        G.add_node(node_id, label=name, title=f"Typ: {node_type}", color=color)

    # Add edges
    for edge in edges:
        source_id = edge["source_id"]
        target_id = edge["target_id"]
        relation = edge["relation_type"]
        G.add_edge(source_id, target_id, label=relation, title=relation)

    # Filtering logic
    if args.filter:
        logger.info(f"Filtere Graph nach: {args.filter}")
        target_node_ids = set()
        filters_lower = [f.lower() for f in args.filter]

        for node_id, data in G.nodes(data=True):
            label_lower = data.get("label", "").lower()
            if any(f in label_lower for f in filters_lower):
                target_node_ids.add(node_id)

        if target_node_ids:
            # Find all ancestors for all target nodes
            nodes_to_expand = set()
            for tid in target_node_ids:
                nodes_to_expand.add(tid)
                nodes_to_expand.update(nx.ancestors(G, tid))

            # Find all descendants of all ancestors (and the target nodes themselves)
            result_nodes = set()
            for node in nodes_to_expand:
                result_nodes.add(node)
                result_nodes.update(nx.descendants(G, node))

            G = G.subgraph(result_nodes).copy()
            logger.info(f"Graph auf {len(G.nodes)} Knoten und {len(G.edges)} Kanten gefiltert.")
        else:
            logger.warning(f"Keine Knoten mit den Namen {args.filter} gefunden.")

    # Create Pyvis network
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)

    # Configure physics for better layout
    net.force_atlas_2based()

    # Load NetworkX graph into Pyvis
    net.from_nx(G)

    # Save visualization
    output_path = config.config_dir.parent / "knowledge_graph.html"
    net.save_graph(str(output_path))

    logger.info(f"Visualisierung wurde unter {output_path} gespeichert.")

if __name__ == "__main__":
    main()
