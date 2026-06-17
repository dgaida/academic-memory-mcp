"""Modul für das Crawlen und Indexieren von Dokumenten und E-Mails."""
import os
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from ..config import Config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..retrieval.index import SearchIndex

logger = logging.getLogger(__name__)

class Crawler:
    """Crawlt konfigurierte Ordner und indexiert deren Inhalte."""

    def __init__(self, config: Config, store: MetadataStore, parser: ParserFactory, summarizer: Summarizer, index: SearchIndex) -> None:
        """Initialisiert den Crawler.

        Args:
            config (Config): Systemkonfiguration.
            store (MetadataStore): Metadaten-Speicher.
            parser (ParserFactory): Parser-Fabrik.
            summarizer (Summarizer): Engine für Zusammenfassungen.
            index (SearchIndex): Suchindex.
        """
        self.config = config
        self.store = store
        self.parser = parser
        self.summarizer = summarizer
        self.index = index

    def crawl(self) -> None:
        """Führt den Crawl-Prozess für alle konfigurierten Ordner aus."""
        for folder_path in self.config.folders.folders:
            path = Path(folder_path)
            if path.exists():
                logger.info(f"Crawling folder: {path}")
                self._process_directory(path)
            else:
                logger.warning(f"Configured folder does not exist: {path}")

    def _process_directory(self, dir_path: Path, parent_id: Optional[int] = None, relative_path: Optional[Path] = None) -> Tuple[Optional[str], bool]:
        """Verarbeitet ein Verzeichnis rekursiv."""
        if relative_path is None:
            relative_path = Path(dir_path.name)
        logger.info(f"Scanning directory: {dir_path} (relative: {relative_path})")

        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        # folder_id = self.store.upsert_folder(str(dir_path), parent_id)
        folder_id = 1 # Dummy

        db_files = self.store.get_folder_files(folder_id)
        current_files = set()
        any_changed = False

        # Check for email conversation (special handling)
        if (dir_path / "Inbox").exists() or (dir_path / "SentItems").exists():
            email_summary, email_changed = self._process_email_conversation(dir_path, folder_id, relative_path)
            if email_changed:
                any_changed = True

        item_summaries = []

        # Subdirectories process
        for entry in os.scandir(dir_path):
            if entry.is_dir():
                # Correct pattern check
                is_excluded = False
                for pattern in self.config.folders.exclude_patterns:
                    if re.match(pattern, entry.name):
                        is_excluded = True
                        break
                if is_excluded:
                    continue
                sub_summary, sub_changed = self._process_directory(Path(entry.path), folder_id, relative_path / entry.name)
                if sub_summary:
                    item_summaries.append(f"ORDNER {entry.name}:\n{sub_summary}")
                if sub_changed:
                    any_changed = True
            elif entry.is_file():
                file_path = Path(entry.path)
                if file_path.suffix.lower() not in self.config.folders.supported_extensions:
                    continue

                is_excluded = False
                for pattern in self.config.folders.exclude_patterns:
                    if re.match(pattern, entry.name):
                        is_excluded = True
                        break
                if is_excluded:
                    continue

                current_files.add(str(file_path))
                file_summary, file_changed = self._process_file(file_path, folder_id)
                if file_summary:
                    item_summaries.append(f"DATEI {entry.name}:\n{file_summary}")
                if file_changed:
                    any_changed = True

        # Handle deleted files
        for db_file in db_files:
            if db_file[1] not in current_files:
                logger.info(f"File {db_file[1]} deleted. Removing from database (Dummy).")
                # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                # self.store.delete_file(db_file[0])
                any_changed = True

        # Folder summary
        folder_summary = None
        if item_summaries:
            existing_folder_summary = self.store.get_summary("folder", folder_id)
            if any_changed or not existing_folder_summary:
                logger.info(f"Generating summary for folder: {relative_path}")
                folder_summary = self.summarizer.summarize_folder(str(relative_path), item_summaries)
                if folder_summary:
                    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                    # self.store.add_summary("folder", folder_id, folder_summary)
                    self._save_summary_to_file(dir_path, folder_summary)
            else:
                folder_summary = existing_folder_summary

        return folder_summary, any_changed

    def _process_email_conversation(self, dir_path: Path, folder_id: int, relative_path: Path) -> Tuple[Optional[str], bool]:
        """Verarbeitet eine E-Mail-Konversation."""
        inbox_path = dir_path / "Inbox"
        sent_path = dir_path / "SentItems"

        email_files = []
        for p in [inbox_path, sent_path]:
            if p.exists():
                for entry in os.scandir(p):
                    if entry.is_file() and entry.name.lower().endswith((".eml", ".msg")):
                        email_files.append(Path(entry.path))

        if not email_files:
            return None, False

        summary_file_path = dir_path / ".emails_summary.md"

        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        if summary_file_path.exists():
             return summary_file_path.read_text(encoding="utf-8"), False

        logger.info(f"Processing {len(email_files)} emails in {dir_path.name}")
        return None, False

    def _process_file(self, file_path: Path, folder_id: int) -> Tuple[Optional[str], bool]:
        """Verarbeitet eine einzelne Datei."""
        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        file_hash = self._calculate_hash(file_path)
        existing_file = self.store.get_file(str(file_path))
        if existing_file:
            if existing_file[2] == file_hash:
                return self.store.get_summary("file", existing_file[0]), False

        content = self.parser.parse(file_path)
        if not content:
            return None, False

        summary = self.summarizer.summarize_file(file_path.name, content)
        if not summary:
            return None, False

        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        # self.store.upsert_file(...)
        return summary, True

    def _calculate_hash(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _save_summary_to_file(self, dir_path: Path, summary: str) -> None:
        summary_path = dir_path.parent / f".{dir_path.name}_summary.md"
        try:
            summary_path.write_text(summary, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save folder summary: {e}")
