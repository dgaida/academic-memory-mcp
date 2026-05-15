"""Modul für das Crawling des Dateisystems."""
import os
import subprocess
import hashlib
from pathlib import Path
import logging
from typing import Optional, Tuple, List

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


    def _process_directory(self, dir_path: Path, parent_id: Optional[int] = None) -> Tuple[Optional[str], bool]:
        """Verarbeitet ein Verzeichnis rekursiv.

        Args:
            dir_path (Path): Das zu verarbeitende Verzeichnis.
            parent_id (Optional[int]): ID des übergeordneten Ordners in der DB.

        Returns:
            Tuple[Optional[str], bool]: (Zusammenfassung des Ordners, Wurde etwas geändert?)
        """
        logger.info(f"Scanning directory: {dir_path}")
        folder_id = self.store.upsert_folder(str(dir_path), parent_id)

        db_files = self.store.get_folder_files(folder_id)
        current_files = set()
        any_changed = False
        item_summaries = []

        # Check for email conversation pattern
        subdirs = [d.name for d in os.scandir(dir_path) if d.is_dir()]
        conv_summary = None
        conv_changed = False
        if "Inbox" in subdirs and "SentItems" in subdirs:
            logger.info(f"Detected email conversation pattern in {dir_path}")
            conv_summary, conv_changed = self._process_email_conversation(dir_path, folder_id)
            if conv_summary:
                item_summaries.append(conv_summary)
            if conv_changed:
                any_changed = True

        for entry in os.scandir(dir_path):
            entry_path = Path(entry.path)
            if entry.is_dir():
                if entry.name in self.config.folders.exclude_patterns:
                    logger.debug(f"Skipping excluded directory: {entry.name}")
                    continue

                # Skip Inbox and SentItems if they were already handled as a conversation
                if entry.name in ["Inbox", "SentItems"] and conv_summary is not None:
                    continue

                sub_summary, sub_changed = self._process_directory(entry_path, folder_id)
                if sub_summary:
                    item_summaries.append(sub_summary)
                if sub_changed:
                    any_changed = True
            elif entry.is_file():
                suffix = entry_path.suffix.lower()
                if suffix not in self.config.folders.supported_extensions:
                    continue
                if entry.name.startswith(".") and (entry.name.endswith("_summary.md") or entry.name.endswith(".emails_summary.md")):
                    continue

                current_files.add(str(entry_path))

                file_summary, file_changed = self._process_file(entry_path, folder_id)
                if file_summary:
                    item_summaries.append(file_summary)
                if file_changed:
                    any_changed = True

        # Handle deleted files
        for db_file in db_files:
            # db_file: (id, path, hash, mtime, type, last_indexed, folder_id)
            if db_file[1] not in current_files:
                logger.info(f"File {db_file[1]} deleted. Removing from database.")
                self.store.delete_file(db_file[0])
                any_changed = True

        existing_folder_summary = self.store.get_summary("folder", folder_id)

        folder_summary = None
        if item_summaries:
            if any_changed or not existing_folder_summary:
                logger.info(f"Generating folder summary for: {dir_path.name}")
                folder_summary = self.summarizer.summarize_folder(dir_path.name, item_summaries)
                if folder_summary:
                    self.store.add_summary("folder", folder_id, folder_summary)
                    self.store.update_folder_summarized(folder_id)
                    self._save_summary_to_file(dir_path, folder_summary)
                    any_changed = True # Folder summary itself changed
            else:
                logger.info(f"Folder {dir_path.name} unchanged. Skipping re-summarization.")
                folder_summary = existing_folder_summary

        return folder_summary, any_changed

    def _process_email_conversation(self, dir_path: Path, folder_id: int) -> Tuple[Optional[str], bool]:
        """Verarbeitet eine E-Mail-Konversation (Inbox & SentItems)."""
        email_files = []
        for sub in ["Inbox", "SentItems"]:
            sub_path = dir_path / sub
            if sub_path.exists():
                for entry in os.scandir(sub_path):
                    if entry.is_file() and entry.name.lower().endswith((".eml", ".msg")):
                        email_files.append(Path(entry.path))

        if not email_files:
            return None, False

        # Calculate a combined hash of all emails to detect changes
        email_files.sort() # Sort by path for consistent hash
        combined_data = ""
        for f in email_files:
            combined_data += f"{f.name}:{f.stat().st_mtime}:{f.stat().st_size}|"
        combined_hash = hashlib.sha256(combined_data.encode()).hexdigest()

        summary_file_path = dir_path / ".emails_summary.md"
        # Use a special item_type for conversation summaries to avoid conflict with normal folder summary
        # Actually, the user wants it to be indexed and treated as part of the folder content.
        # We'll use a specific key in the DB to check for changes.

        db_folder = self.store._get_connection().execute("SELECT identity_json FROM folders WHERE id=?", (folder_id,)).fetchone()

        if db_folder and db_folder[0] == combined_hash and summary_file_path.exists():
            logger.info(f"Email conversation in {dir_path.name} unchanged.")
            return summary_file_path.read_text(encoding="utf-8"), False

        logger.info(f"Processing {len(email_files)} emails for conversation summary in {dir_path.name}")

        # Sort emails chronologically
        dated_emails = []
        for f in email_files:
            date = self.parser.mail_parser.get_email_date(f)
            dated_emails.append((date, f))

        dated_emails.sort(key=lambda x: x[0])

        conversation_text = ""
        for date, f in dated_emails:
            parsed = self.parser.mail_parser.parse(f)
            if parsed:
                conversation_text += f"\n--- EMAIL VOM {date} ---\n{parsed}\n"

        summary = self.summarizer.summarize_email_conversation(dir_path.name, conversation_text)
        if summary:
            # Store hash in identity_json
            with self.store._get_connection() as conn:
                conn.execute("UPDATE folders SET identity_json = ? WHERE id = ?", (combined_hash, folder_id))
                conn.commit()

            # Save to file
            try:
                summary_file_path.write_text(summary, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to save email summary for {dir_path.name}: {e}")

            # Index the summary
            self.index.add_document(str(summary_file_path), summary, {
                "path": str(summary_file_path),
                "folder": str(dir_path),
                "filename": ".emails_summary.md",
                "type": ".md",
                "is_conversation_summary": "true"
            })

            return summary, True

        return None, False

    def _process_file(self, file_path: Path, folder_id: int) -> Tuple[Optional[str], bool]:
        """Verarbeitet eine einzelne Datei (Parsing -> Summarization -> Indexierung).

        Args:
            file_path (Path): Pfad zur Datei.
            folder_id (int): ID des zugehörigen Ordners.

        Returns:
            Tuple[Optional[str], bool]: (Zusammenfassung der Datei, Wurde sie neu/geändert indexiert?)
        """
        logger.debug(f"Processing file: {file_path}")
        mtime = file_path.stat().st_mtime
        file_hash = self._calculate_hash(file_path)

        existing_file = self.store.get_file(str(file_path))
        if existing_file:
            if existing_file[2] == file_hash:
                logger.debug(f"File {file_path} unchanged. Skipping.")
                return self.store.get_summary("file", existing_file[0]), False

        logger.info(f"Indexing new or changed file: {file_path}")
        content = self.parser.parse(file_path)
        if not content:
            logger.warning(f"Failed to parse content for {file_path}")
            return None, False

        summary = self.summarizer.summarize_file(file_path.name, content)
        if not summary:
            logger.warning(f"Failed to generate summary for {file_path}")
            return None, False

        file_id = self.store.upsert_file(str(file_path), file_hash, mtime, file_path.suffix.lower(), folder_id)
        self.store.add_summary("file", file_id, summary)

        # Wir indexieren die Zusammenfassung statt des vollen Inhalts
        self.index.add_document(str(file_path), summary, {
            "path": str(file_path),
            "folder": str(file_path.parent),
            "filename": file_path.name,
            "type": file_path.suffix.lower()
        })

        return summary, True
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
