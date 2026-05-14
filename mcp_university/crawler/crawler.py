"""Modul für das Crawling des Dateisystems."""
import os
import subprocess
import hashlib
from pathlib import Path
import logging
from typing import Optional

from ..config import Config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..retrieval.index import SearchIndex

logger = logging.getLogger(__name__)

class Crawler:
    """Komponente zum Durchsuchen des Dateisystems und zur Indexierung von Dokumenten.

    Verantwortlich für das rekursive Scannen von Verzeichnissen, das Erkennen von Änderungen
    via Hashes und die Koordination von Parsing, Summarization und Indexierung.
    """

    def __init__(self, config: Config, store: MetadataStore, parser: ParserFactory, summarizer: Summarizer, index: SearchIndex):
        """Initialisiert den Crawler mit notwendigen Abhängigkeiten.

        Args:
            config (Config): Systemkonfiguration.
            store (MetadataStore): Metadaten-Speicher.
            parser (ParserFactory): Factory für Dokumenten-Parser.
            summarizer (Summarizer): Dienst für Zusammenfassungen.
            index (SearchIndex): Suchindex-Schnittstelle.
        """
        self.config = config
        self.store = store
        self.parser = parser
        self.summarizer = summarizer
        self.index = index
        self.use_shell = os.name == 'nt'

    def _calculate_hash(self, path: Path) -> str:
        """Berechnet den SHA-256 Hash einer Datei.

        Args:
            path (Path): Pfad zur Datei.

        Returns:
            str: Der hexadezimale Hash-String.
        """
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def crawl(self) -> None:
        """Startet den Crawling-Prozess für alle konfigurierten Ordner.
        """
        logger.info("Starting crawl process...")
        for root_path_str in self.config.folders.folders:
            root_path = Path(root_path_str)
            if not root_path.exists():
                logger.warning(f"Root path {root_path} does not exist. Skipping.")
                continue

            logger.info(f"Processing root folder: {root_path}")
            # qmd integration (with Windows fix)
            coll_name = root_path.name
            exts = [ext.lstrip('.') for ext in self.config.folders.supported_extensions]
            mask = f"**/*.{{{','.join(exts)}}}"

            logger.debug(f"Syncing qmd collection '{coll_name}' for {root_path}")
            try:
                subprocess.run([
                    "qmd", "collection", "add", str(root_path),
                    "--name", coll_name,
                    "--mask", mask
                ], capture_output=True, shell=self.use_shell)
            except Exception as e:
                logger.debug(f"qmd collection add skipped or failed: {e}")

            # Process the directory and generate the final summary for the root
            self._process_directory(root_path)

        logger.info("Updating qmd index...")
        try:
            subprocess.run(["qmd", "update"], capture_output=True, shell=self.use_shell)
        except Exception as e:
            logger.debug(f"qmd update skipped or failed: {e}")

        logger.info("Crawl process completed.")

    def _process_directory(self, dir_path: Path, parent_id: Optional[int] = None) -> Optional[str]:
        """Verarbeitet ein Verzeichnis rekursiv.

        Args:
            dir_path (Path): Das zu verarbeitende Verzeichnis.
            parent_id (Optional[int]): ID des übergeordneten Ordners in der DB.

        Returns:
            Optional[str]: Die Zusammenfassung des Ordners.
        """
        logger.info(f"Scanning directory: {dir_path}")
        folder_id = self.store.upsert_folder(str(dir_path), parent_id)

        item_summaries = []

        for entry in os.scandir(dir_path):
            if entry.is_dir():
                # Skip excluded folders
                if entry.name in self.config.folders.exclude_patterns:
                    logger.debug(f"Skipping excluded directory: {entry.name}")
                    continue
                subfolder_summary = self._process_directory(Path(entry.path), folder_id)
                if subfolder_summary:
                    item_summaries.append(subfolder_summary)
            elif entry.is_file():
                # Skip excluded files
                suffix = Path(entry.name).suffix.lower()
                if suffix not in self.config.folders.supported_extensions:
                    continue
                # Skip hidden summary files themselves to avoid recursion/clutter
                if entry.name.startswith(".") and entry.name.endswith("_summary.md"):
                    continue

                file_summary = self._process_file(Path(entry.path), folder_id)
                if file_summary:
                    item_summaries.append(file_summary)

        # Generate folder summary
        folder_summary = None
        if item_summaries:
            logger.info(f"Generating folder summary for: {dir_path.name}")
            folder_summary = self.summarizer.summarize_folder(dir_path.name, item_summaries)
            if folder_summary:
                self.store.add_summary("folder", folder_id, folder_summary)
                self._save_summary_to_file(dir_path, folder_summary)

        return folder_summary

    def _save_summary_to_file(self, dir_path: Path, summary: str) -> None:
        """Speichert die Ordner-Zusammenfassung als versteckte Markdown-Datei im Elternverzeichnis.

        Args:
            dir_path (Path): Pfad zum zusammengefassten Ordner.
            summary (str): Der Inhalt der Zusammenfassung.
        """
        parent_dir = dir_path.parent
        summary_filename = f".{dir_path.name}_summary.md"
        summary_path = parent_dir / summary_filename

        try:
            logger.debug(f"Saving folder summary to: {summary_path}")
            summary_path.write_text(summary, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save folder summary for {dir_path.name}: {e}")

    def _process_file(self, file_path: Path, folder_id: int) -> Optional[str]:
        """Verarbeitet eine einzelne Datei (Parsing -> Summarization -> Indexierung).

        Args:
            file_path (Path): Pfad zur Datei.
            folder_id (int): ID des zugehörigen Ordners.

        Returns:
            Optional[str]: Die Zusammenfassung der Datei oder None.
        """
        logger.debug(f"Processing file: {file_path}")
        mtime = file_path.stat().st_mtime
        file_hash = self._calculate_hash(file_path)

        existing_file = self.store.get_file(str(file_path))
        if existing_file:
            if existing_file[2] == file_hash:
                logger.info(f"File {file_path} unchanged. Skipping.")
                # We still need the summary for the folder summary aggregation.
                # Retrieve existing summary from DB.
                # summaries: id, item_type, item_id, content, version, created_at
                with self.store._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT content FROM summaries WHERE item_type = "file" AND item_id = ? ORDER BY created_at DESC LIMIT 1',
                        (existing_file[0],)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else None

        logger.info(f"Indexing new or changed file: {file_path}")
        content = self.parser.parse(file_path)
        if not content:
            logger.warning(f"Failed to parse content for {file_path}")
            return None

        summary = self.summarizer.summarize_file(file_path.name, content)
        if not summary:
            logger.warning(f"Failed to generate summary for {file_path}")
            return None

        file_id = self.store.upsert_file(str(file_path), file_hash, mtime, file_path.suffix.lower(), folder_id)
        self.store.add_summary("file", file_id, summary)

        # Index via SearchIndex (handles qmd and native fallback)
        self.index.add_document(str(file_path), content, {
            "path": str(file_path),
            "folder": str(file_path.parent),
            "filename": file_path.name,
            "type": file_path.suffix.lower()
        })

        return summary
