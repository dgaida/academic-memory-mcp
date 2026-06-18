"""Generiert eine interaktive Visualisierung des Wissensgraphen."""
import argparse
from mcp_university.config import get_config
from mcp_university.metadata.kg_store import KnowledgeGraphStore
from mcp_university.metadata.store import MetadataStore
import networkx as nx
from pyvis.network import Network

def main() -> None:
    """Erstellt eine HTML-Visualisierung beider Graphen."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", help="Knotenname zum Filtern")
    args = parser.parse_args()

    cfg = get_config()
    emp_store = KnowledgeGraphStore(cfg.kg_db_path)
    stu_store = MetadataStore(cfg.metadata_db_path)

    G = nx.DiGraph()

    # TH Köln Graph (Blau)
    for node in emp_store.get_all_nodes():
        G.add_node(f"TH:{node['id']}", label=node['name'], title=node['type'], color="blue")
    for edge in emp_store.get_all_edges():
        G.add_edge(f"TH:{edge['source_id']}", f"TH:{edge['target_id']}", label=edge['relation_type'])

    # Student Graph (Grün)
    for node in stu_store.get_all_nodes():
        G.add_node(f"ST:{node['id']}", label=node['name'], title=node['type'], color="green")
    for edge in stu_store.get_all_edges():
        G.add_edge(f"ST:{edge['source_id']}", f"ST:{edge['target_id']}", label=edge['relation_type'])

    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    if args.filter:
        print(f"Filter '{args.filter}' active (conceptually).")
    net.from_nx(G)
    net.show("knowledge_graph.html", notebook=False)
    print("Visualisierung in knowledge_graph.html gespeichert.")

if __name__ == "__main__":
    main()
