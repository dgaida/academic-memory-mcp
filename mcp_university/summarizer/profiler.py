import json
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper
from mcp_university.metadata.store import MetadataStore
from mcp_university.metadata.profile_store import ProfileStore

logger = logging.getLogger(__name__)

class PersonProfiler:
    """Klasse zur Erstellung und Verwaltung von Personen-Steckbriefen aus E-Mails."""

    def __init__(self, storage_path: Path = Path(r"D:\Steckbriefe")) -> None:
        """Initialisiert den PersonProfiler.

        Args:
            storage_path (Path): Pfad, in dem die Steckbriefe gespeichert werden.
        """
        self.storage_path = storage_path
        self.config = get_config()
        self.mail_parser = MailParser()
        self.llm = LLMClientWrapper()
        self.store = MetadataStore(self.config.sqlite_path)
        self.profile_store = ProfileStore(self.config.data_dir / "profiles_tracking.db")

        # Sicherstellen, dass das Speicherverzeichnis existiert
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Konnte Speicherverzeichnis {self.storage_path} nicht erstellen: {e}. Nutze lokales Verzeichnis 'Steckbriefe'.")
            self.storage_path = Path("Steckbriefe")
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_search_paths(self) -> List[Path]:
        """Gibt alle zu durchsuchenden Pfade aus der Konfiguration zurück.

        Returns:
            List[Path]: Liste der Pfade.
        """
        paths = []

        # Aus classifier_paths.yaml
        cp_path = self.config.config_dir / "classifier_paths.yaml"
        if cp_path.exists():
            with open(cp_path, "r", encoding="utf-8") as f:
                cp_data = yaml.safe_load(f)
                class_paths = cp_data.get("class_paths", {})
                for p in class_paths.values():
                    paths.append(Path(p))

        # Aus train_test_folders.yaml
        ttf_path = self.config.config_dir / "train_test_folders.yaml"
        if ttf_path.exists():
            with open(ttf_path, "r", encoding="utf-8") as f:
                ttf_data = yaml.safe_load(f)
                if "train_path" in ttf_data:
                    paths.append(Path(ttf_data["train_path"]))
                if "test_path" in ttf_data:
                    paths.append(Path(ttf_data["test_path"]))

        return [p for p in paths if p.exists()]

    def find_emails_for_address(self, email_address: str) -> List[Dict[str, Any]]:
        """Sucht rekursiv nach E-Mails von oder an die angegebene Adresse.

        Args:
            email_address (str): Die zu suchende E-Mail-Adresse.

        Returns:
            List[Dict[str, Any]]: Liste der gefundenen E-Mails mit Metadaten.
        """
        email_address = email_address.lower()
        search_paths = self.get_search_paths()
        found_emails = []

        for path in search_paths:
            for file_path in path.rglob("*"):
                if file_path.suffix.lower() in [".msg", ".eml"]:
                    try:
                        if file_path.suffix.lower() == ".msg":
                            details = self.mail_parser._get_msg_details(file_path)
                        else:
                            details = self.mail_parser._get_eml_details(file_path)

                        if not details:
                            continue

                        # Check sender
                        match = False
                        if details.get("from_email", "").lower() == email_address:
                            match = True

                        # Check recipients
                        if not match:
                            for rec in details.get("to", []):
                                if rec.get("email", "").lower() == email_address:
                                    match = True
                                    break

                        if not match:
                            for rec in details.get("cc", []):
                                if rec.get("email", "").lower() == email_address:
                                    match = True
                                    break

                        if match:
                            found_emails.append({
                                "path": file_path,
                                "date": details.get("date") or datetime.min,
                                "details": details
                            })
                    except Exception as e:
                        logger.error(f"Fehler beim Parsen von {file_path}: {e}")

        # Sortieren nach Datum aufsteigend
        found_emails.sort(key=lambda x: x["date"])
        return found_emails

    def create_batches(self, emails: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Teilt E-Mails in Batches auf, basierend auf der Zeitlücke.

        Args:
            emails (List[Dict[str, Any]]): Sortierte Liste von E-Mails.

        Returns:
            List[List[Dict[str, Any]]]: Liste von E-Mail-Batches.
        """
        batches = []
        remaining = emails

        while remaining:
            if len(remaining) <= 10:
                batches.append(remaining)
                break

            # Betrachte die ersten 5-10 Mails
            sample_size = min(len(remaining), 10)

            max_gap = -1
            split_idx = sample_size

            for i in range(1, sample_size):
                gap = (remaining[i]["date"] - remaining[i-1]["date"]).total_seconds()
                if gap > max_gap:
                    max_gap = gap
                    split_idx = i

            batches.append(remaining[:split_idx])
            remaining = remaining[split_idx:]

        return batches



    def _get_knowledge_graph_context(self, email_address: str) -> str:
        """Sucht im Wissensgraphen nach Informationen über die Person.

        Verfolgt ausgehende Kanten mittels Tiefensuche (DFS), um Fakultät, Institut etc. zu finden.

        Args:
            email_address (str): E-Mail-Adresse der Person.

        Returns:
            str: Formatierte Informationen aus dem Wissensgraphen.
        """
        person_node = self.store.get_node_by_property("email", email_address)
        if not person_node:
            return ""

        context_parts = []
        visited_nodes = set()
        to_visit = [(person_node["id"], 0)]  # (node_id, depth)

        while to_visit:
            node_id, depth = to_visit.pop()
            if node_id in visited_nodes or depth > 3:
                continue

            visited_nodes.add(node_id)
            node = self.store.get_node_by_id(node_id)
            if not node:
                continue

            node_name = node["name"]
            node_type = node["type"]
            props = json.loads(node.get("properties_json", "{}"))

            info = f"- {node_name} ({node_type})"
            if props:
                prop_str = ", ".join([f"{k}: {v}" for k, v in props.items()])
                info += f" [Eigenschaften: {prop_str}]"

            context_parts.append("  " * depth + info)

            # Nachbarn finden (ausgehende Kanten)
            edges = self.store.get_outgoing_edges(node_id)
            for edge in edges:
                target_node_id = edge["target_id"]
                to_visit.append((target_node_id, depth + 1))

        if not context_parts:
            return ""

        return "\nInformationen aus dem Wissensgraphen:\n" + "\n".join(context_parts)

    def generate_profile(self, email_address: str, force_update: bool = False) -> Optional[str]:
        """Erstellt oder aktualisiert einen Steckbrief für die angegebene Adresse.

        Args:
            email_address (str): E-Mail-Adresse der Person.
            force_update (bool): Ob die Aktualisierung erzwungen werden soll.

        Returns:
            Optional[str]: Der Inhalt des Steckbriefs oder None bei Fehler.
        """
        profile_file = self.storage_path / f"{email_address}.md"

        if profile_file.exists() and not force_update:
            logger.info(f"Steckbrief für {email_address} existiert bereits.")
            return profile_file.read_text(encoding="utf-8")

        is_tool_user = email_address.lower() == self.config.user.email.lower()
        emails = [] if is_tool_user else self.find_emails_for_address(email_address)
        kg_context = self._get_knowledge_graph_context(email_address)

        if is_tool_user:
            user_info = f"Informationen aus der Konfiguration (user.yaml):\n- Name: {self.config.user.name}\n- E-Mail: {self.config.user.email}\n"
            kg_context = user_info + kg_context

        if not emails and not kg_context:
            logger.warning(f"Keine E-Mails und keine Wissensgraph-Infos für {email_address} gefunden.")
            return None

        batches = self.create_batches(emails) if emails else [[]]
        current_profile = ""

        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\n"
                batch_content += f"Betreff: {details['subject']}\n"
                batch_content += f"Inhalt: {details['body'][:1000]}...\n"

            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        # Speichern
        profile_file.write_text(current_profile, encoding="utf-8")
        
        # Tracking aktualisieren
        if emails:
            filenames = [m["path"].name for m in emails]
            self.profile_store.add_processed_emails(email_address, filenames)

        return current_profile

    def update_profile(self, email_address: str) -> Optional[str]:
        """Aktualisiert den Steckbrief einer Person, falls neue E-Mails vorhanden sind.

        Für den Tool-Nutzer (user.yaml) wird der Steckbrief nur aus dem Wissensgraphen
        und der Konfiguration aktualisiert, nicht aus E-Mails.

        Args:
            email_address (str): E-Mail-Adresse der Person.

        Returns:
            Optional[str]: Der aktualisierte (oder bestehende) Steckbrief.
        """
        profile_file = self.storage_path / f"{email_address}.md"
        if not profile_file.exists():
            return self.generate_profile(email_address)

        is_tool_user = email_address.lower() == self.config.user.email.lower()
        if is_tool_user:
            # Für den Tool-Nutzer aktualisieren wir immer aus dem KG (einfach neu generieren)
            return self.generate_profile(email_address, force_update=True)

        existing_profile = profile_file.read_text(encoding="utf-8")
        processed_files = self.profile_store.get_processed_filenames(email_address)
        
        all_emails = self.find_emails_for_address(email_address)
        new_emails = [m for m in all_emails if m["path"].name not in processed_files]

        if not new_emails:
            logger.info(f"Keine neuen E-Mails für {email_address} gefunden.")
            return existing_profile

        logger.info(f"{len(new_emails)} neue E-Mails für {email_address} gefunden. Aktualisiere Steckbrief...")
        
        kg_context = self._get_knowledge_graph_context(email_address)
        batches = self.create_batches(new_emails)
        current_profile = existing_profile

        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Update-Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\n"
                batch_content += f"Betreff: {details['subject']}\n"
                batch_content += f"Inhalt: {details['body'][:1000]}...\n"

            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        # Speichern und Tracking aktualisieren
        profile_file.write_text(current_profile, encoding="utf-8")
        new_filenames = [m["path"].name for m in new_emails]
        self.profile_store.add_processed_emails(email_address, new_filenames)
        
        return current_profile

    def update_all_profiles(self) -> None:
        """Aktualisiert alle existierenden Steckbriefe."""
        if not self.storage_path.exists():
            return

        for profile_file in self.storage_path.glob("*.md"):
            email_address = profile_file.stem
            # Einfache Validierung ob es eine E-Mail ist
            if "@" in email_address:
                logger.info(f"Prüfe Update für {email_address}...")
                self.update_profile(email_address)

    def get_profile(self, email_address: str) -> Optional[str]:
        """Gibt den Steckbrief zurück (und aktualisiert ihn ggf.).

        Args:
            email_address (str): E-Mail-Adresse.

        Returns:
            Optional[str]: Steckbrief-Inhalt.
        """
        return self.update_profile(email_address)

    def _get_profiling_prompt(self, email: str, new_content: str, existing_profile: str, kg_context: str = "") -> str:
        """Erstellt den Prompt für das LLM.

        Args:
            email (str): E-Mail-Adresse.
            new_content (str): Neuer E-Mail-Inhalt (Batch).
            existing_profile (str): Bisheriger Steckbrief.
            kg_context (str): Informationen aus dem Wissensgraphen.

        Returns:
            str: Der formatierte Prompt.
        """
        if not existing_profile:
            context = "Dies ist der Beginn der Analyse. Erstelle einen neuen Steckbrief."
        else:
            context = f"Bisheriger Steckbrief:\n\n{existing_profile}\n\nAktualisiere diesen Steckbrief mit den folgenden neuen Informationen."

        kg_info = f"\n{kg_context}\n" if kg_context else ""
        email_info = f"\nHier sind die neuen E-Mails:\n{new_content}\n" if new_content else ""

        return f"""Du bist ein Assistent, der Personen-Steckbriefe aus E-Mails und Informationen aus einem Wissensgraphen erstellt.
Die Zielperson hat die E-Mail-Adresse: {email}

{context}

{kg_info}{email_info}
Erstelle einen strukturierten Steckbrief in Markdown mit folgenden Punkten:
1. Name und E-Mailadresse
2. Rolle (z.B. Studierende, Lehrende, Mitarbeiter, Professor, externer Partner, ...)
3. Bevorzugte Anrede (Du oder Sie? Analyse basierend auf dem Ton der E-Mails)
4. Datum des ersten Kontakts
5. Wichtige Stationen/Ereignisse:
   - Bei Mitarbeitern: Wichtige Aufgaben, Projekte, Zuständigkeiten.
   - Bei Professoren: Gelesene Module, Forschungsprojekte, Gremienarbeit.
   - Bei Studierenden: Abgeschlossene Projektarbeiten/Thesen, Wechsel der Prüfungsordnung, Praktika, etc.
   - Sonstiges: Alle weiteren relevanten Informationen aus dem Mailverlauf.

Verhalte dich objektiv und sachlich. Antworte NUR mit dem Markdown-Inhalt des Steckbriefs.
"""
