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
        """Initialisiert die Search Engine und den Vorschlags-Cache.

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

        # Vorschlags-Cache initialisieren
        self.suggestions_cache_file = self.cache_file.parent / "suggestions_cache.json"
        self._load_suggestions_cache()

    def _load_cache(self) -> None:
        """Lädt den Index aus dem Cache.

        Returns:
            None
        """
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(f"Cache geladen: {len(self.index)} E-Mails.")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Caches: {e}")
                self.index = []

    def _save_cache(self) -> None:
        """Speichert den Index im Cache.

        Returns:
            None
        """
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            logger.info("Cache gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Caches: {e}")

    def _load_suggestions_cache(self) -> None:
        """Lädt den Vorschlags-Cache aus der JSON-Datei oder initialisiert ihn mit Defaults.

        Returns:
            None
        """
        self.suggestions_cache: Set[str] = set()

        # Standardbegriffe im Hochschulkontext
        default_university_terms = {
            "Informatik", "Bachelor", "Master", "Thesis", "Bachelorarbeit", "Masterarbeit",
            "Projektarbeit", "Prüfung", "Klausur", "Kolloquium", "Forschung", "Vorlesung",
            "Seminar", "Übung", "Professor", "Prüfungsordnung", "Studiengang",
            "Nachteilsausgleich", "Sprechstunde", "Zulassung", "Anmeldung", "Abgabe",
            "Note", "Zweitprüfer", "Erstprüfer", "Praxissemester", "Modul", "Hochschule",
            "Studierende", "Mitarbeiter", "Dekanat", "Präsidium", "Lehrveranstaltung"
        }

        if self.suggestions_cache_file.exists():
            try:
                with open(self.suggestions_cache_file, "r", encoding="utf-8") as f:
                    cached_list = json.load(f)
                    self.suggestions_cache = set(cached_list)
                logger.info(f"Vorschlags-Cache geladen: {len(self.suggestions_cache)} Begriffe.")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Vorschlags-Caches: {e}")
                self.suggestions_cache = set()

        if not self.suggestions_cache:
            self.suggestions_cache.update(default_university_terms)
            self._add_index_elements_to_suggestions()
            self._save_suggestions_cache()

    def _add_index_elements_to_suggestions(self) -> None:
        """Fügt alle Namen und E-Mail-Adressen aus dem Index zum Vorschlags-Cache hinzu.

        Returns:
            None
        """
        for item in self.index:
            if item.get("from_name"):
                self.suggestions_cache.add(item["from_name"])
            if item.get("from"):
                self.suggestions_cache.add(item["from"])

            # Empfänger ebenfalls hinzufügen (to)
            to_list = item.get("to", [])
            for rec in to_list:
                if isinstance(rec, dict):
                    if rec.get("name"):
                        self.suggestions_cache.add(rec["name"])
                    if rec.get("email"):
                        self.suggestions_cache.add(rec["email"])
                elif isinstance(rec, str):
                    self.suggestions_cache.add(rec)

    def _save_suggestions_cache(self) -> None:
        """Speichert den Vorschlags-Cache in der JSON-Datei und leert den LRU-Cache.

        Returns:
            None
        """
        try:
            self.suggestions_cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.suggestions_cache_file, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.suggestions_cache)), f, ensure_ascii=False, indent=2)
            logger.info("Vorschlags-Cache gespeichert.")
            try:
                self.get_suggestions.cache_clear()
            except AttributeError:
                pass
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Vorschlags-Caches: {e}")

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

        Returns:
            None
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
                        parts_lower = [p.lower() for p in file_path.parts]
                        sent_folder_names_lower = [
                            "sentitems", "sent items", "gesendete elemente",
                            "gesendete objekte", "sent"
                        ]
                        if any(sf in parts_lower for sf in sent_folder_names_lower):
                            folder_type = "SentItems"

                        new_index.append({
                            "subject": details.get("subject", ""),
                            "from": details.get("from_email", ""),
                            "from_name": details.get("from_name", ""),
                            "to": details.get("to", []),
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
        # Aktualisiere Vorschlags-Cache mit den neuen Elementen
        self._add_index_elements_to_suggestions()
        self._save_suggestions_cache()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Sucht nach E-Mails im Index.

        Args:
            query (str): Der Suchbegriff.

        Returns:
            List[Dict[str, Any]]: Liste der Treffer.
        """
        if not query:
            return []

        # Neuen Suchbegriff zum Cache hinzufügen
        stripped_query = query.strip()
        if len(stripped_query) >= 2:
            if stripped_query not in self.suggestions_cache:
                self.suggestions_cache.add(stripped_query)
                self._save_suggestions_cache()

        query_lower = query.lower()
        results = []
        for item in self.index:
            found = (query_lower in item.get("subject", "").lower() or
                     query_lower in item.get("from", "").lower() or
                     query_lower in item.get("from_name", "").lower() or
                     query_lower in item.get("filename", "").lower() or
                     query_lower in item.get("path", "").lower())

            if not found and "to" in item:
                to_list = item["to"]
                for rec in to_list:
                    if isinstance(rec, dict):
                        rec_name = rec.get("name", "")
                        rec_email = rec.get("email", "")
                        if query_lower in rec_name.lower() or query_lower in rec_email.lower():
                            found = True
                            break
                    elif isinstance(rec, str):
                        if query_lower in rec.lower():
                            found = True
                            break

            if found:
                results.append(item)

        # Sortiere nach Datum absteigend (neueste zuerst)
        results.sort(key=lambda x: x.get("date", ""), reverse=True)
        return results

    @functools.lru_cache(maxsize=128)
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Gibt Vorschläge für die Suche aus dem Cache und dem aktuellen Index zurück.

        Args:
            partial_query (str): Der bisher eingegebene Suchbegriff.

        Returns:
            List[str]: Liste von Vorschlägen.
        """
        if not partial_query or len(partial_query) < 2:
            return []

        partial_query_lower = partial_query.lower()
        suggestions: Set[str] = set()

        # 1. Aus dem Vorschlags-Cache suchen
        for term in self.suggestions_cache:
            if partial_query_lower in term.lower():
                suggestions.add(term)

        # 2. Aus dem aktuellen In-Memory-Index suchen (falls dort neue/ungespeicherte Objekte sind)
        for item in self.index:
            # Senders
            name = item.get("from_name", "")
            if name and partial_query_lower in name.lower():
                suggestions.add(name)
            email = item.get("from", "")
            if email and partial_query_lower in email.lower():
                suggestions.add(email)

            # Subjects
            subject = item.get("subject", "")
            if subject and partial_query_lower in subject.lower():
                words = re.findall(r'\w+', subject)
                for word in words:
                    if len(word) > 3 and partial_query_lower in word.lower():
                        suggestions.add(word)

            # Recipients
            to_list = item.get("to", [])
            for rec in to_list:
                if isinstance(rec, dict):
                    rec_name = rec.get("name", "")
                    rec_email = rec.get("email", "")
                    if rec_name and partial_query_lower in rec_name.lower():
                        suggestions.add(rec_name)
                    if rec_email and partial_query_lower in rec_email.lower():
                        suggestions.add(rec_email)
                elif isinstance(rec, str):
                    if partial_query_lower in rec.lower():
                        suggestions.add(rec)

        # Sortieren nach Priorität:
        # 1. Begriffe, die mit der Eingabe starten (case-insensitiv)
        # 2. Andere Begriffe, die die Eingabe enthalten
        starts_with = []
        contains = []
        for term in suggestions:
            if term.lower().startswith(partial_query_lower):
                starts_with.append(term)
            else:
                contains.append(term)

        sorted_suggestions = sorted(starts_with) + sorted(contains)

        # Limitiere auf 10 Vorschläge
        return sorted_suggestions[:10]
