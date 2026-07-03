"""Modul für die schnelle Suche nach E-Mails in konfigurierten Pfaden."""

import json
import logging
import yaml
import re
import functools
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser

logger = logging.getLogger(__name__)

class EmailSearchEngine:
    """Engine für die schnelle Suche nach E-Mails mit Caching."""

    def __init__(self, cache_file: Optional[Path] = None) -> None:
        """Initialisiert die Search Engine.

        Args:
            cache_file (Path, optional): Pfad zur Cache-Datei.
        """
        self.config = get_config()
        if cache_file is None:
            self.cache_file = self.config.data_dir / "cache" / "email_search_cache.json"
        else:
            self.cache_file = cache_file

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.mail_parser = MailParser()
        self.index: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Lädt den Index aus dem Cache."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(f"Cache geladen: {len(self.index)} E-Mails.")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Caches: {e}")
                self.index = []

    def _save_cache(self) -> None:
        """Speichert den Index im Cache."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            logger.info("Cache gespeichert.")
            # Cache für Vorschläge leeren, wenn sich der Index ändert
            self.get_suggestions.cache_clear()
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Caches: {e}")

    def get_search_paths(self) -> List[Path]:
        """Ermittelt alle zu durchsuchenden Pfade aus der Konfiguration.

        Returns:
            List[Path]: Liste der Pfade.
        """
        paths = []

        # 1. classifier_paths.yaml
        cp_path = self.config.config_dir / "classifier_paths.yaml"
        if not cp_path.exists():
            cp_path = self.config.config_dir / "classifier_paths.yaml.example"

        if cp_path.exists():
            try:
                with open(cp_path, "r", encoding="utf-8") as f:
                    cp_data = yaml.safe_load(f)
                    if cp_data and "class_paths" in cp_data:
                        for p in cp_data["class_paths"].values():
                            path = Path(p)
                            if path.exists():
                                paths.append(path)
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {cp_path}: {e}")

        # 2. train_test_folders.yaml
        ttf_path = self.config.config_dir / "train_test_folders.yaml"
        if ttf_path.exists():
            try:
                with open(ttf_path, "r", encoding="utf-8") as f:
                    ttf_data = yaml.safe_load(f)
                    if ttf_data:
                        for key in ["train_path", "test_path"]:
                            if key in ttf_data:
                                path = self.config.config_dir.parent / ttf_data[key]
                                if path.exists():
                                    paths.append(path)
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {ttf_path}: {e}")

        return list(set(paths))

    def update_index(self, force: bool = False) -> None:
        """Durchsucht die Pfade und aktualisiert den Index.

        Args:
            force (bool): Wenn True, wird der Index komplett neu aufgebaut.
        """
        search_paths = self.get_search_paths()
        logger.info(f"Aktualisiere Index für Pfade: {search_paths}")

        indexed_paths = {item["path"] for item in self.index} if not force else set()
        new_index = self.index if not force else []

        for base_path in search_paths:
            for file_path in base_path.rglob("*"):
                if file_path.suffix.lower() in [".msg", ".eml"]:
                    path_str = str(file_path.absolute())
                    if path_str in indexed_paths:
                        continue

                    try:
                        details = self.mail_parser.get_email_details(file_path)
                        # Sicherstellen, dass das Datum ein String ist für JSON
                        date_val = details.get("date")
                        if isinstance(date_val, datetime):
                            date_str = date_val.isoformat()
                        else:
                            date_str = str(date_val)

                        # Ordner bestimmen (Inbox oder SentItems)
                        folder_type = "Inbox"
                        if "SentItems" in file_path.parts:
                            folder_type = "SentItems"

                        new_index.append({
                            "subject": details.get("subject", ""),
                            "from": details.get("from_email", ""),
                            "from_name": details.get("from_name", ""),
                            "date": date_str,
                            "path": path_str,
                            "filename": file_path.name,
                            "folder": folder_type
                        })
                        indexed_paths.add(path_str)
                    except Exception as e:
                        logger.error(f"Fehler beim Indizieren von {file_path}: {e}")

        self.index = new_index
        self._save_cache()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Sucht nach E-Mails im Index.

        Args:
            query (str): Der Suchbegriff.

        Returns:
            List[Dict[str, Any]]: Liste der Treffer.
        """
        if not query:
            return []

        query = query.lower()
        results = []
        for item in self.index:
            if (query in item["subject"].lower() or
                query in item["from"].lower() or
                query in item["from_name"].lower() or
                query in item["filename"].lower()):
                results.append(item)

        # Sortiere nach Datum absteigend (neueste zuerst)
        results.sort(key=lambda x: x["date"], reverse=True)
        return results

    @functools.lru_cache(maxsize=128)
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Gibt Vorschläge für die Suche zurück.

        Args:
            partial_query (str): Der bisher eingegebene Suchbegriff.

        Returns:
            List[str]: Liste von Vorschlägen.
        """
        if not partial_query or len(partial_query) < 2:
            return []

        partial_query = partial_query.lower()
        suggestions: Set[str] = set()

        for item in self.index:
            # Vorschläge aus Absendernamen
            name = item["from_name"]
            if name and partial_query in name.lower():
                suggestions.add(name)

            # Vorschläge aus E-Mail-Adressen
            email = item["from"]
            if email and partial_query in email.lower():
                suggestions.add(email)

            # Vorschläge aus Betreff (Wörter)
            subject = item["subject"]
            if subject and partial_query in subject.lower():
                words = re.findall(r'\w+', subject)
                for word in words:
                    if len(word) > 3 and partial_query in word.lower():
                        suggestions.add(word)

        # Limitiere auf 10 Vorschläge
        return sorted(list(suggestions), key=len)[:10]
