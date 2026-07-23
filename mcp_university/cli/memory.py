"""CLI commands for memory management."""
import typer
import logging
import yaml
from pathlib import Path
from transformers import AutoTokenizer
from ..config import get_config
from academic_parser.factory import ParserFactory
from ..retrieval.index import SearchIndex
from ..utils.memory import resolve_memory_index_names
from scripts.index_memory import process_memory_folder

memory_app = typer.Typer(help="Verwaltung des Memory-Systems (Vektordatenbanken)")

@memory_app.command("update")
def memory_update(
    config: str = typer.Option("config/classifier_memory_paths.yaml", "--config", "-c", help="Pfad zur Speicherpfad-Konfiguration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")
) -> None:
    """Aktualisiert die Vektordatenbanken für das Memory basierend auf neuen Inhalten."""
    from .main import setup_logging
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    config_path = Path(config)
    if not config_path.exists():
        logger.error(f"Konfigurationsdatei {config_path} nicht gefunden.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    class_paths = config_data.get("class_paths", {})
    if not class_paths:
        logger.error("Keine class_paths in der Konfiguration gefunden.")
        return

    # Resolve shared index names
    class_to_index = resolve_memory_index_names(class_paths)

    # Map index names to unique paths
    index_to_path = {}
    for class_name, path_str in class_paths.items():
        index_name = class_to_index[class_name]
        if index_name not in index_to_path:
            index_to_path[index_name] = Path(path_str)

    global_config = get_config()
    tokenizer = AutoTokenizer.from_pretrained(global_config.embeddings.model)
    parser_factory = ParserFactory(cache_dir=global_config.data_dir / "cache")

    memory_base_dir = global_config.data_dir / "memory"
    memory_base_dir.mkdir(parents=True, exist_ok=True)

    for index_name, base_path in index_to_path.items():
        if not base_path.exists():
            logger.warning(f"Pfad {base_path} für Index {index_name} existiert nicht. Überspringe.")
            continue

        print(f"Aktualisiere Memory-Index '{index_name}'...")
        index_dir = memory_base_dir / index_name
        index = SearchIndex(location=str(index_dir), embedding_model_name=global_config.embeddings.model)

        process_memory_folder(index_name, base_path, index, parser_factory, tokenizer)
        print(f"Index '{index_name}' erfolgreich aktualisiert.")
