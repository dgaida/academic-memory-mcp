"""Skript zum Aufbau des Wissensgraphen aus extrahierten E-Mail-Zusammenfassungen."""
import sys
from pathlib import Path
import yaml
import logging

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from mcp_university.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """Hauptfunktion zum Aufbau des Wissensgraphen."""
    config = get_config()
    # store = MetadataStore(config.sqlite_path)

    # Check if Qdrant path exists
    qdrant_path = config.qdrant_path
    qdrant_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Initialize User Node
    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
    user_node_id = 1
    print(f"User node initialized (Dummy): {config.user.name} (ID: {user_node_id})")

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

    # 3. Ontology Learning (Personen-Aliase aus E-Mails)
    logger.info("Starte vorbereitendes Ontology-Lernen...")
    for base_path_str in class_paths.values():
        base_path = Path(base_path_str)
        if base_path.exists():
            # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
            pass

    # 4. Iterate through paths and build graph
    for class_name, base_path_str in class_paths.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            logger.warning(f"Path does not exist: {base_path}")
            continue

        logger.info(f"Processing class {class_name} in {base_path}")

        # Recursive search for .emails_summary.md
        for summary_file in base_path.rglob(".emails_summary.md"):
            logger.info(f"Processing existing summary: {summary_file}")
            # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
            # changes = graph_engine.process_summary(...)
            changes = {}
            if any(changes.values()):
                logger.info(f"Changes from {summary_file.name}:")
            else:
                logger.info(f"No new information extracted from {summary_file.name}.")

        # Also look for the alternative naming pattern .<dirname>_summary.md
        for summary_file in base_path.rglob(".*_summary.md"):
            if summary_file.name == ".emails_summary.md":
                continue
            logger.info(f"Processing folder summary: {summary_file}")
            # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
            # changes = graph_engine.process_summary(...)
            changes = {}
            if any(changes.values()):
                logger.info(f"Changes from {summary_file.name}:")
            else:
                logger.info(f"No new information extracted from {summary_file.name}.")

    # 5. Modul-Ontologie-Lernen (nachdem Knoten existieren)
    logger.info("Prüfe auf Modul-Duplikate...")
    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.

    logger.info("Knowledge Graph build complete.")

if __name__ == "__main__":
    main()
