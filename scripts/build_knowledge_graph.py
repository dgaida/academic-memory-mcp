import sys
from pathlib import Path
import yaml
import logging

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from mcp_university.config import get_config
from mcp_university.metadata.store import MetadataStore
from mcp_university.summarizer.engine import Summarizer
from mcp_university.knowledge_graph.engine import KnowledgeGraphEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    config = get_config()
    store = MetadataStore(config.sqlite_path)
    summarizer = Summarizer(model=config.llm.model, base_url=config.llm.base_url)

    # Check if Qdrant path exists
    qdrant_path = config.qdrant_path
    qdrant_path.parent.mkdir(parents=True, exist_ok=True)

    graph_engine = KnowledgeGraphEngine(store, summarizer)

    # 1. Initialize User Node
    user_node_id, _ = store.upsert_node(config.user.name, "Person", {"email": config.user.email, "role": ["User"]})
    logger.info(f"Initialized user node: {config.user.name} (ID: {user_node_id})")

    # 2. Load classifier_paths.yaml
    paths_file = config.config_dir / "classifier_paths.yaml"
    if not paths_file.exists():
        paths_file = config.config_dir / "classifier_paths.yaml.example"

    if not paths_file.exists():
        logger.error("classifier_paths.yaml not found.")
        return

    with open(paths_file, "r", encoding="utf-8") as f:
        paths_data = yaml.safe_load(f)

    class_paths = paths_data.get("class_paths", {})

    # 3. Iterate through paths and build graph
    for class_name, base_path_str in class_paths.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            logger.warning(f"Path does not exist: {base_path}")
            continue

        logger.info(f"Processing class {class_name} in {base_path}")

        # Ensure summaries are created by running a crawl on the base_path
        # Note: Crawler.crawl takes a list of folders from config. But we want to target these specific ones.
        # We temporarily update config or just call the internal processing.

        # Recursive search for .emails_summary.md
        for summary_file in base_path.rglob(".emails_summary.md"):
            logger.info(f"Processing existing summary: {summary_file}")
            content = summary_file.read_text(encoding="utf-8")
            changes = graph_engine.process_summary(content, user_node_id)
            if any(changes.values()):
                logger.info(f"Changes from {summary_file.name}:")
                if changes['new_nodes']:
                    logger.info(f"  New Nodes: {', '.join(changes['new_nodes'])}")
                if changes['new_edges']:
                    logger.info(f"  New Edges:")
                    for edge in changes['new_edges']:
                        logger.info(f"    - {edge}")
            else:
                logger.info(f"No new information extracted from {summary_file.name}.")

        # Also look for the alternative naming pattern .<dirname>_summary.md
        for summary_file in base_path.rglob(".*_summary.md"):
            if summary_file.name == ".emails_summary.md":
                continue
            logger.info(f"Processing folder summary: {summary_file}")
            content = summary_file.read_text(encoding="utf-8")
            changes = graph_engine.process_summary(content, user_node_id)
            if any(changes.values()):
                logger.info(f"Changes from {summary_file.name}:")
                if changes['new_nodes']:
                    logger.info(f"  New Nodes: {', '.join(changes['new_nodes'])}")
                if changes['new_edges']:
                    logger.info(f"  New Edges:")
                    for edge in changes['new_edges']:
                        logger.info(f"    - {edge}")
            else:
                logger.info(f"No new information extracted from {summary_file.name}.")

    logger.info("Knowledge Graph build complete.")

if __name__ == "__main__":
    main()
