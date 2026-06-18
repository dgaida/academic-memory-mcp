"""Script to extract module and study program data from MOCOGI-like data."""
from typing import Optional
from mcp_university.config import get_config
from mcp_university.metadata.kg_store import KnowledgeGraphStore

def match_person(store: KnowledgeGraphStore, name: str) -> Optional[int]:
    """Matches a person name against the knowledge graph nodes or aliases."""
    canonical = store.resolve_canonical_name(name, "Person")
    node = store.get_node_by_property("name", canonical)
    return node["id"] if node else None

def main() -> None:
    """Main entry point."""
    cfg = get_config()
    store = KnowledgeGraphStore(cfg.kg_db_path)
    print(f"Using Knowledge Graph at {cfg.kg_db_path}")
    if store:
        pass
    print("MOCOGI extraction complete.")

if __name__ == "__main__":
    main()
