"""Modul zur Erstellung von Personen-Steckbriefen."""
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
from mcp_university.metadata.kg_store import KnowledgeGraphStore
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
        # MetadataStore für studentische Verbindungen (metadata.db)
        self.student_store = MetadataStore(self.config.metadata_db_path)
        # KnowledgeGraphStore für TH Köln Personal (knowledge_graph.db)
        self.employee_store = KnowledgeGraphStore(self.config.kg_db_path)
        self.profile_store = ProfileStore(self.config.profiles_db_path)

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
        cp_path = self.config.config_dir / "classifier_paths.yaml"
        if cp_path.exists():
            with open(cp_path, "r", encoding="utf-8") as f:
                cp_data = yaml.safe_load(f)
                class_paths = cp_data.get("class_paths", {})
                for p in class_paths.values():
                    paths.append(Path(p))

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

                        match = False
                        if details.get("from_email", "").lower() == email_address:
                            match = True
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
        found_emails.sort(key=lambda x: x["date"])
        return found_emails

    def create_batches(self, emails: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Teilt E-Mails in Batches auf.

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
        """Sucht in beiden Wissensgraphen nach Informationen über die Person.

        Args:
            email_address (str): E-Mail-Adresse der Person.

        Returns:
            str: Formatierte Informationen.
        """
        context_parts = []

        # 1. Check Employee Store (TH Köln Personnel)
        emp_node = self.employee_store.get_node_by_property("email", email_address)
        if emp_node:
            context_parts.append("\nInformationen aus dem Wissensgraphen:")
            context_parts.extend(self._traverse_graph(self.employee_store, emp_node["id"]))

        # 2. Check Student Store (Student-User Relationships)
        stu_node = self.student_store.get_node_by_property("email", email_address)
        if stu_node:
            context_parts.append("\nInformationen aus dem studentischen Wissensgraphen:")
            context_parts.extend(self._traverse_graph(self.student_store, stu_node["id"]))

        return "\n".join(context_parts) if context_parts else ""

    def _traverse_graph(self, store: Any, start_node_id: int) -> List[str]:
        """Traversiert den Graphen ab einem Startknoten.

        Args:
            store (Any): Der zu durchsuchende Store.
            start_node_id (int): Startknoten-ID.

        Returns:
            List[str]: Formatierte Zeilen.
        """
        parts = []
        visited = set()
        to_visit = [(start_node_id, 0)]
        while to_visit:
            node_id, depth = to_visit.pop()
            if node_id in visited or depth > 3:
                continue
            visited.add(node_id)
            node = store.get_node_by_id(node_id)
            if not node:
                continue
            props = json.loads(node.get("properties_json", "{}"))
            info = f"- {node['name']} ({node['type']})"
            if props:
                p_str = ", ".join([f"{k}: {v}" for k, v in props.items()])
                info += f" [{p_str}]"
            parts.append("  " * depth + info)
            for edge in store.get_outgoing_edges(node_id):
                to_visit.append((edge["target_id"], depth + 1))
        return parts

    def generate_profile(self, email_address: str, force_update: bool = False) -> Optional[str]:
        """Erstellt oder aktualisiert einen Steckbrief.

        Args:
            email_address (str): E-Mail-Adresse der Person.
            force_update (bool): Ob Aktualisierung erzwungen werden soll.

        Returns:
            Optional[str]: Der Inhalt des Steckbriefs.
        """
        profile_file = self.storage_path / f"{email_address}.md"
        if profile_file.exists() and not force_update:
            return profile_file.read_text(encoding="utf-8")

        is_tool_user = email_address.lower() == self.config.user.email.lower()
        emails = [] if is_tool_user else self.find_emails_for_address(email_address)
        kg_context = self._get_knowledge_graph_context(email_address)

        if is_tool_user:
            kg_context = f"Infos aus user.yaml:\n- Name: {self.config.user.name}\n- E-Mail: {self.config.user.email}\n" + kg_context

        if not emails and not kg_context:
            return None

        batches = self.create_batches(emails) if emails else [[]]
        current_profile = ""
        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\nBetreff: {details['subject']}\nInhalt: {details['body'][:1000]}...\n"
            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        profile_file.write_text(current_profile, encoding="utf-8")
        if emails:
            self.profile_store.add_processed_emails(email_address, [m["path"].name for m in emails])
        return current_profile

    def update_profile(self, email_address: str) -> Optional[str]:
        """Aktualisiert den Steckbrief.

        Args:
            email_address (str): E-Mail-Adresse.

        Returns:
            Optional[str]: Der Steckbrief.
        """
        profile_file = self.storage_path / f"{email_address}.md"
        if not profile_file.exists():
            return self.generate_profile(email_address)

        is_tool_user = email_address.lower() == self.config.user.email.lower()
        if is_tool_user:
            return self.generate_profile(email_address, force_update=True)

        existing_profile = profile_file.read_text(encoding="utf-8")
        processed_files = self.profile_store.get_processed_filenames(email_address)
        all_emails = self.find_emails_for_address(email_address)
        new_emails = [m for m in all_emails if m["path"].name not in processed_files]

        if not new_emails:
            return existing_profile

        kg_context = self._get_knowledge_graph_context(email_address)
        batches = self.create_batches(new_emails)
        current_profile = existing_profile
        for i, batch in enumerate(batches):
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\nBetreff: {details['subject']}\nInhalt: {details['body'][:1000]}...\n"
            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        profile_file.write_text(current_profile, encoding="utf-8")
        self.profile_store.add_processed_emails(email_address, [m["path"].name for m in new_emails])
        return current_profile

    def update_all_profiles(self) -> None:
        """Aktualisiert alle Steckbriefe."""
        if not self.storage_path.exists():
            return
        for profile_file in self.storage_path.glob("*.md"):
            email_address = profile_file.stem
            if "@" in email_address:
                self.update_profile(email_address)

    def get_profile(self, email_address: str) -> Optional[str]:
        """Gibt den Steckbrief zurück.

        Args:
            email_address (str): E-Mail-Adresse.

        Returns:
            Optional[str]: Inhalt.
        """
        return self.update_profile(email_address)

    def _get_profiling_prompt(self, email: str, new_content: str, existing_profile: str, kg_context: str = "") -> str:
        """Erstellt den Prompt.

        Args:
            email (str): E-Mail.
            new_content (str): Neuer Inhalt.
            existing_profile (str): Vorheriger Steckbrief.
            kg_context (str): Graph-Kontext.

        Returns:
            str: Prompt.
        """
        context = ""
        if existing_profile:
            context = f"Bisheriger Steckbrief:\n\n{existing_profile}\n\nAktualisiere diesen."
        else:
            context = "Neuer Steckbrief."

        kg_info = ""
        if kg_context:
            kg_info = f"\n{kg_context}\n"

        email_info = ""
        if new_content:
            email_info = f"\nNeue E-Mails:\n{new_content}\n"

        return f"Du bist ein Assistent für Personen-Steckbriefe an der TH Köln. Zielperson: {email}\n\n{context}\n\n{kg_info}{email_info}\n\nErstelle Markdown: 1. Name/Email, 2. Rolle, 3. Anrede, 4. Erster Kontakt, 5. Stationen (Projekte, Module, Thesen). Sachlich bleiben. Hier sind die neuen E-Mails: NUR Markdown."
