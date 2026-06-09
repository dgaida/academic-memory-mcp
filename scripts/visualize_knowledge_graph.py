import sys
import os
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

def main():
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
        "User": "#00ff00"         # Green
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
