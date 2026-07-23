"""Script to index memory folders into a vector database."""
import yaml
import argparse
import logging
import os
from pathlib import Path
from typing import List, Any, Set
from tqdm import tqdm
from transformers import AutoTokenizer

from mcp_university.retrieval.index import SearchIndex
from academic_parser.factory import ParserFactory
from mcp_university.config import get_config
from mcp_university.utils.memory import resolve_memory_index_names
from mcp_university.utils.shortcuts import resolve_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def chunk_text(text: str, tokenizer: Any, chunk_size: int = 512, overlap: int = 100) -> List[str]:
    """Splits text into chunks using a tokenizer.

    Args:
        text (str): The text to chunk.
        tokenizer (Any): Tokenizer instance.
        chunk_size (int): Max number of tokens per chunk.
        overlap (int): Number of tokens to overlap between chunks.

    Returns:
        List[str]: List of text chunks.
    """
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i : i + chunk_size]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + chunk_size >= len(tokens):
            break
    return chunks

def get_all_files(base_path: Path, supported_extensions: List[str]) -> List[Path]:
    """
    Finds all files in base_path, following symlinks and resolving shortcuts.
    Avoids infinite recursion and duplicate processing.

    Args:
        base_path (Path): Base directory to search.
        supported_extensions (List[str]): List of supported file extensions.

    Returns:
        List[Path]: List of files to process.
    """
    files_to_process = []
    seen_paths: Set[str] = set()

    def _collect(current_path: Path):
        """Recursively collects files while handling links and avoiding cycles.

        Args:
            current_path (Path): The current path to explore.
        """
        resolved = resolve_path(current_path)
        if not resolved.exists():
            return

        resolved_str = str(resolved.absolute())
        if resolved_str in seen_paths:
            return
        seen_paths.add(resolved_str)

        if resolved.is_file():
            if resolved.suffix.lower() in supported_extensions:
                files_to_process.append(resolved)
        elif resolved.is_dir():
            try:
                for entry in os.scandir(resolved):
                    _collect(Path(entry.path))
            except PermissionError:
                logger.warning(f"Permission denied for directory: {resolved}")

    _collect(base_path)
    return files_to_process

def process_memory_folder(index_name: str, base_path: Path, index: SearchIndex, parser_factory: ParserFactory, tokenizer: Any) -> None:
    """Traverses a folder, parses files, chunks them and adds to the index.

    Args:
        index_name (str): Name of the index.
        base_path (Path): Path to the folder to process.
        index (SearchIndex): Search index instance.
        parser_factory (ParserFactory): Parser factory instance.
        tokenizer (Any): Tokenizer instance.
    """
    logger.info(f"Processing memory index '{index_name}' from path: {base_path}")

    supported_extensions = [".pdf", ".docx", ".md", ".txt", ".eml", ".msg", ".py", ".ipynb", ".json", ".html"]

    files_to_process = get_all_files(base_path, supported_extensions)

    if not files_to_process:
        logger.warning(f"No supported files found in {base_path}")
        return

    all_chunks = []
    for file_path in tqdm(files_to_process, desc=f"Parsing {index_name}"):
        try:
            content = parser_factory.parse(file_path)
            if not content:
                continue

            chunks = chunk_text(content, tokenizer, chunk_size=512, overlap=100)

            for i, chunk in enumerate(chunks):
                doc_id = f"{file_path.absolute()}_chunk_{i}"
                all_chunks.append({
                    "doc_id": doc_id,
                    "content": chunk,
                    "metadata": {
                        "source_file": str(file_path),
                        "memory_index": index_name,
                        "chunk_index": i
                    }
                })
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    if all_chunks:
        logger.info(f"Indexing {len(all_chunks)} chunks for {index_name}...")
        # Index in batches to avoid overhead
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            index.add_documents(all_chunks[i:i + batch_size])
    else:
        logger.warning(f"No content extracted for {index_name}")

def main() -> None:
    """Main entry point for memory indexing script."""
    academic_parser = argparse.ArgumentParser(description="Index memory files into vector databases.")
    academic_parser.add_argument("--config", type=str, default="config/classifier_memory_paths.yaml", help="Path to the memory paths yaml.")
    args = academic_parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file {config_path} not found.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    class_paths = config_data.get("class_paths", {})
    if not class_paths:
        logger.error("No class_paths found in config.")
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
            logger.warning(f"Path {base_path} for index {index_name} does not exist. Skipping.")
            continue

        index_dir = memory_base_dir / index_name
        index = SearchIndex(location=str(index_dir), embedding_model_name=global_config.embeddings.model)

        process_memory_folder(index_name, base_path, index, parser_factory, tokenizer)

if __name__ == "__main__":
    main()
