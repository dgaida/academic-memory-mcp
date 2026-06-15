"""Skript zur interaktiven Visualisierung des Wissensgraphen mittels Pyvis."""
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
    parser.add_argument("--filter", type=str, help="Filtert den Graphen nach einem Knotenamen (zeigt die verbundene Komponente).")
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
        target_node_id = None
        filter_lower = args.filter.lower()
        for node_id, data in G.nodes(data=True):
            if filter_lower in data.get("label", "").lower():
                target_node_id = node_id
                break

        if target_node_id is not None:
            # Find connected component in undirected version
            UG = G.to_undirected()
            connected_nodes = nx.node_connected_component(UG, target_node_id)
            G = G.subgraph(connected_nodes).copy()
            logger.info(f"Graph auf {len(G.nodes)} Knoten und {len(G.edges)} Kanten gefiltert.")
        else:
            logger.warning(f"Kein Knoten mit dem Namen '{args.filter}' gefunden.")

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
