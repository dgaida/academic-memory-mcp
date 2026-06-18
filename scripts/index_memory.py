import yaml
import argparse
import logging
from pathlib import Path
from typing import List, Any
from tqdm import tqdm
from transformers import AutoTokenizer

from mcp_university.retrieval.index import SearchIndex
from mcp_university.parser.factory import ParserFactory
from mcp_university.config import get_config
from mcp_university.utils.memory import resolve_memory_index_names

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def chunk_text(text: str, tokenizer: Any, chunk_size: int = 512, overlap: int = 100) -> List[str]:
    """Splits text into chunks using a tokenizer."""
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i : i + chunk_size]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + chunk_size >= len(tokens):
            break
    return chunks

def process_memory_folder(index_name: str, base_path: Path, index: SearchIndex, parser_factory: ParserFactory, tokenizer: Any):
    """Traverses a folder, parses files, chunks them and adds to the index."""
    logger.info(f"Processing memory index '{index_name}' from path: {base_path}")

    supported_extensions = [".pdf", ".docx", ".md", ".txt", ".eml", ".msg", ".py", ".ipynb", ".json", ".html"]

    files_to_process = []
    for ext in supported_extensions:
        files_to_process.extend(list(base_path.rglob(f"*{ext}")))

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

def main():
    parser = argparse.ArgumentParser(description="Index memory files into vector databases.")
    parser.add_argument("--config", type=str, default="config/classifier_memory_paths.yaml", help="Path to the memory paths yaml.")
    args = parser.parse_args()

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
        index = SearchIndex(location=index_dir, embedding_model_name=global_config.embeddings.model)

        process_memory_folder(index_name, base_path, index, parser_factory, tokenizer)

if __name__ == "__main__":
    main()
