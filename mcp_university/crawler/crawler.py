"""Crawler zur Überwachung von Ordnern und Indexierung von Dateien."""
import os
import logging
import hashlib
import subprocess
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from ..config import Config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..retrieval.index import SearchIndex

logger = logging.getLogger(__name__)

class Crawler:
    """Überwacht konfigurierte Ordner und indexiert neue oder geänderte Dateien."""

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
        self.use_shell = os.name == 'nt'

    def crawl(self) -> None:
        """Startet einen vollständigen Scan aller konfigurierten Ordner."""
        logger.info("Starting full crawl...")
        for folder_path in self.config.folders.folders:
            path = Path(folder_path)
            if path.exists() and path.is_dir():
                logger.info(f"Processing root folder: {path}")
                # qmd integration (with Windows fix)
                coll_name = path.name
                exts = [ext.lstrip('.') for ext in self.config.folders.supported_extensions]
                mask = f"**/*.{{{','.join(exts)}}}"

                logger.debug(f"Syncing qmd collection '{coll_name}' for {path}")
                try:
                    subprocess.run([
                        "qmd", "collection", "add", str(path),
                        "--name", coll_name,
                        "--mask", mask
                    ], capture_output=True, shell=self.use_shell)
                except Exception as e:
                    logger.debug(f"qmd collection add skipped or failed: {e}")

                self._process_directory(path)
            else:
                logger.warning(f"Configured folder does not exist or is not a directory: {folder_path}")

        logger.info("Updating qmd index...")
        try:
            subprocess.run(["qmd", "update"], capture_output=True, shell=self.use_shell)
        except Exception as e:
            logger.debug(f"qmd update skipped or failed: {e}")

        logger.info("Crawl completed.")

    def _process_directory(self, dir_path: Path, parent_id: Optional[int] = None, relative_path: Optional[Path] = None) -> Tuple[Optional[str], bool]:
        """Verarbeitet einen Ordner rekursiv.

        Args:
            dir_path (Path): Pfad zum Ordner.
            parent_id (Optional[int]): ID des übergeordneten Ordners in der DB.

        Returns:
            Tuple[Optional[str], bool]: (Zusammenfassung des Ordners, Wurde etwas geändert?)
        """
        if relative_path is None:
            relative_path = Path(dir_path.name)
        logger.info(f"Scanning directory: {dir_path} (relative: {relative_path})")
        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        folder_id = 1 # Dummy

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
            conv_summary, conv_changed = self._process_email_conversation(dir_path, folder_id, relative_path)
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

                sub_summary, sub_changed = self._process_directory(entry_path, folder_id, relative_path / entry_path.name)
                if sub_summary:
                    item_summaries.append(sub_summary)
                if sub_changed:
                    any_changed = True
            elif entry.is_file():
                suffix = entry_path.suffix.lower()
                if suffix not in self.config.folders.supported_extensions:
                    continue
                if entry.name.startswith(".") and entry.name.endswith("_summary.md"):
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
                # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                # self.store.delete_file(db_file[0])
                any_changed = True

        existing_folder_summary = self.store.get_summary("folder", folder_id)
        summary_path = self._get_summary_path(dir_path, parent_id)

        folder_summary = None
        if item_summaries:
            if any_changed or not existing_folder_summary or not summary_path.exists():
                logger.info(f"Generating folder summary for: {relative_path}")
                folder_summary = self.summarizer.summarize_folder(str(relative_path), item_summaries)

                if not folder_summary:
                    logger.error(f"Failed to generate folder summary for: {relative_path}. Retrying with enhanced logging and debug files...")

                    # Enhanced debugging: Write items to debug files
                    items_debug_path = dir_path / ".folder_summary_items_debug.txt"
                    combined_debug_path = dir_path / ".folder_summary_combined_debug.txt"

                    combined_content = "\n-----ITEM-BOUNDARY-----\n".join(item_summaries)

                    try:
                        items_debug_path.write_text("\n\n".join(item_summaries), encoding="utf-8")
                        combined_debug_path.write_text(combined_content, encoding="utf-8")
                        logger.info(f"Debug files written to: {dir_path}")
                    except Exception as e:
                        logger.warning(f"Failed to write debug files: {e}")

                    logger.info(f"Folder summary debug info: {len(item_summaries)} items, total length: {len(combined_content)} chars")

                    # Retry
                    folder_summary = self.summarizer.summarize_folder(str(relative_path), item_summaries)

                if folder_summary:
                    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                    # self.store.add_summary("folder", folder_id, folder_summary)
                    # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                    # self.store.update_folder_summarized(folder_id)
                    self._save_summary_to_file(dir_path, folder_summary, parent_id)
                    any_changed = True # Folder summary itself changed
                else:
                    logger.error(f"Final failure to generate folder summary for: {relative_path} after retry.")
            else:
                logger.info(f"Folder {dir_path.name} unchanged. Skipping re-summarization.")
                folder_summary = existing_folder_summary

        return folder_summary, any_changed

    def _process_email_conversation(self, dir_path: Path, folder_id: int, relative_path: Path) -> Tuple[Optional[str], bool]:
        """Verarbeitet eine E-Mail-Konversation (Inbox & SentItems) gruppiert nach Personen."""
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

        # Calculate a combined hash of all emails to detect changes
        email_files.sort()
        combined_data = ""
        for f in email_files:
            combined_data += f"{f.name}:{f.stat().st_mtime}:{f.stat().st_size}|"
        combined_hash = hashlib.sha256(combined_data.encode()).hexdigest()

        summary_file_path = dir_path / ".emails_summary.md"

        db_folder = self.store._get_connection().execute("SELECT identity_json FROM folders WHERE id=?", (folder_id,)).fetchone()

        if db_folder and db_folder[0] == combined_hash and summary_file_path.exists():
            logger.info(f"Email conversation in {dir_path.name} unchanged.")
            return summary_file_path.read_text(encoding="utf-8"), False

        logger.info(f"Processing {len(email_files)} emails for grouped conversation summary in {dir_path.name}")

        user_email = self.config.user.email.lower()

        # Group emails by counterpart
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for f in email_files:
            details = self.parser.mail_parser.get_email_details(f)
            details["file_path"] = f

            counterparts = []
            if "Inbox" in str(f.parent):
                # Counterpart is the sender
                if details["from_email"] and details["from_email"] != user_email:
                    counterparts.append(details["from_email"])
                elif details["from_name"]:
                    counterparts.append(details["from_name"])
            else:
                # Counterpart is the recipient (To, Cc)
                for rec in details["to"] + details["cc"]:
                    if rec["email"] and rec["email"] != user_email:
                        counterparts.append(rec["email"])
                    elif rec["name"]:
                        counterparts.append(rec["name"])

            if not counterparts:
                counterparts = ["Unbekannt"]

            for cp in set(counterparts):
                if cp not in groups:
                    groups[cp] = []
                groups[cp].append(details)

        all_summaries = []
        for cp, mails in groups.items():
            # Sort mails newest to oldest
            mails.sort(key=lambda x: x['date'], reverse=True)

            # Log for testing/visibility
            logger.info(f'Order of emails for conversation with {cp}:')
            for m in mails:
                logger.info(f"  - {m['file_path'].name}")

            conversation_content = ''
            if self.config.folders.summarize_emails_individually:
                email_summaries = []
                for m in mails:
                    content_parsed = self.parser.mail_parser.parse(m['file_path'])
                    if content_parsed:
                        summary = self.summarizer.summarize_file(m['file_path'].name, content_parsed)
                        if summary:
                            email_summaries.append(f"--- EMAIL VOM {m['date']} ({m['file_path'].name}) ---\n{summary}")
                conversation_content = '\n\n'.join(email_summaries)
            else:
                for m in mails:
                    parsed = self.parser.mail_parser.parse(m['file_path'])
                    if parsed:
                        conversation_content += f"\n--- EMAIL VOM {m['date']} ({m['file_path'].name}) ---\n{parsed}\n"

            summary = self.summarizer.summarize_email_conversation(f"{relative_path}: Konversation mit {cp}", conversation_content)
            if summary:
                all_summaries.append(summary)
        if all_summaries:
            combined_summary = "\n\n---\n\n".join(all_summaries)

            # Store hash in identity_json
            with self.store._get_connection() as conn:
                # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
                # conn.execute("UPDATE folders SET identity_json = ? WHERE id = ?", (combined_hash, folder_id))
                conn.commit()

            # Save to file
            try:
                summary_file_path.write_text(combined_summary, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to save email summary for {dir_path.name}: {e}")

            # Index the summary
            self.index.add_document(str(summary_file_path), combined_summary, {
                "path": str(summary_file_path),
                "folder": str(dir_path),
                "filename": ".emails_summary.md",
                "type": ".md",
                "is_conversation_summary": "true"
            })

            return combined_summary, True

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

        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        file_id = 1 # Dummy
        # TODO: Dieses Skript muss in Zukunft in eine andere Datenbank schreiben.
        # self.store.add_summary("file", file_id, summary)

        # Wir indexieren die Zusammenfassung statt des vollen Inhalts
        self.index.add_document(str(file_path), summary, {
            "path": str(file_path),
            "folder": str(file_path.parent),
            "filename": file_path.name,
            "type": file_path.suffix.lower()
        })

        return summary, True

    def _calculate_hash(self, file_path: Path) -> str:
        """Berechnet den SHA-256 Hash einer Datei.

        Args:
            file_path (Path): Pfad zur Datei.

        Returns:
            str: Der berechnete Hash.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_summary_path(self, dir_path: Path, parent_id: Optional[int]) -> Path:
        """Bestimmt den Pfad für die Ordner-Zusammenfassungsdatei.

        Speichert die Zusammenfassung im Elternverzeichnis als .{name}_summary.md.
        """
        return dir_path.parent / f".{dir_path.name}_summary.md"

    def _save_summary_to_file(self, dir_path: Path, summary: str, parent_id: Optional[int] = None) -> None:
        """Speichert die Ordner-Zusammenfassung als versteckte Markdown-Datei im Elternverzeichnis.

        Args:
            dir_path (Path): Pfad zum zusammengefassten Ordner.
            summary (str): Der Inhalt der Zusammenfassung.
        """
        summary_path = self._get_summary_path(dir_path, parent_id)

        try:
            logger.info(f"Saving folder summary to: {summary_path}")
            summary_path.write_text(summary, encoding="utf-8")
            if summary_path.exists():
                logger.info(f"Successfully verified existence of summary file: {summary_path}")
            else:
                logger.error(f"Summary file missing after write attempt: {summary_path}")
        except Exception as e:
            logger.error(f"Failed to save folder summary for {dir_path.name}: {e}")
