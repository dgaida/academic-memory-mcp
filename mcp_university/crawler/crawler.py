import os
import subprocess
import hashlib
from pathlib import Path
import logging
from typing import List, Optional
import time

from ..config import Config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..retrieval.index import SearchIndex

logger = logging.getLogger(__name__)

class Crawler:
    def __init__(self, config: Config, store: MetadataStore, parser: ParserFactory, summarizer: Summarizer, index: SearchIndex):
        self.config = config
        self.store = store
        self.parser = parser
        self.summarizer = summarizer
        self.index = index

    def _calculate_hash(self, path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def crawl(self):
        for root_path_str in self.config.folders.folders:
            root_path = Path(root_path_str)
            if not root_path.exists():
                logger.warning(f"Root path {root_path} does not exist. Skipping.")
                continue

            # Ensure the folder is in a qmd collection
            coll_name = root_path.name
            exts = [ext.lstrip('.') for ext in self.config.folders.supported_extensions]
            mask = f"**/*.{{{','.join(exts)}}}"

            logger.info(f"Syncing qmd collection for {root_path}")
            subprocess.run([
                "qmd", "collection", "add", str(root_path),
                "--name", coll_name,
                "--mask", mask
            ], capture_output=True)

            self._process_directory(root_path)

        logger.info("Updating qmd index...")
        subprocess.run(["qmd", "update"], capture_output=True)

    def _process_directory(self, dir_path: Path, parent_id: Optional[int] = None):
        folder_id = self.store.upsert_folder(str(dir_path), parent_id)

        file_summaries = []

        for entry in os.scandir(dir_path):
            if entry.is_dir():
                # Skip excluded folders
                if entry.name in self.config.folders.exclude_patterns:
                    continue
                self._process_directory(Path(entry.path), folder_id)
            elif entry.is_file():
                # Skip excluded files
                suffix = Path(entry.name).suffix.lower()
                if suffix not in self.config.folders.supported_extensions:
                    continue

                file_summary = self._process_file(Path(entry.path), folder_id)
                if file_summary:
                    file_summaries.append(file_summary)

        # After processing all files in folder, generate folder summary if needed
        # (This is a simplified strategy for now)
        if file_summaries:
            folder_summary = self.summarizer.summarize_folder(dir_path.name, file_summaries)
            if folder_summary:
                self.store.add_summary("folder", folder_id, folder_summary)

    def _process_file(self, file_path: Path, folder_id: int) -> Optional[str]:
        mtime = file_path.stat().st_mtime
        file_hash = self._calculate_hash(file_path)

        existing_file = self.store.get_file(str(file_path))
        if existing_file:
            # existing_file: (id, path, hash, mtime, type, last_indexed, folder_id)
            if existing_file[2] == file_hash:
                logger.info(f"File {file_path} unchanged. Skipping.")
                # Return latest summary if it exists
                # In real impl, fetch from DB
                return None

        # Parse file
        content = self.parser.parse(file_path)
        if not content:
            return None

        # Summarize
        summary = self.summarizer.summarize_file(file_path.name, content)
        if not summary:
            return None

        # Store metadata
        file_id = self.store.upsert_file(str(file_path), file_hash, mtime, file_path.suffix.lower(), folder_id)
        self.store.add_summary("file", file_id, summary)

        # Add to index
        self.index.add_document(str(file_path), content, {
            "path": str(file_path),
            "folder": str(file_path.parent),
            "filename": file_path.name,
            "type": file_path.suffix.lower()
        })

        return summary
