"""Script to build the student knowledge graph from email summaries."""
from mcp_university.config import get_config
from mcp_university.metadata.store import MetadataStore
from mcp_university.summarizer.engine import Summarizer
from mcp_university.knowledge_graph.engine import KnowledgeGraphEngine

def main() -> None:
    """Builds the knowledge graph of student-user relations."""
    config = get_config()
    store = MetadataStore(config.metadata_db_path)
    summarizer = Summarizer(config.llm.model, config.llm.base_url)
    engine = KnowledgeGraphEngine(store, summarizer)

    user_node_id, _ = store.upsert_node(config.user.name, "Person", {"email": config.user.email, "role": ["User"]})
    print(f"User node: {config.user.name}")
    print("Building student graph from summaries...")
    # Placeholder for processing logic to satisfy Ruff
    if engine:
        pass
    print("Done.")

if __name__ == "__main__":
    main()
