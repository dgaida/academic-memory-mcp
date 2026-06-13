import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper

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
            List[Path]: Liste der zu durchsuchenden Pfade.
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

        emails = self.find_emails_for_address(email_address)
        if not emails:
            logger.warning(f"Keine E-Mails für {email_address} gefunden.")
            return None

        batches = self.create_batches(emails)
        current_profile = ""

        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\n"
                batch_content += f"Betreff: {details['subject']}\n"
                batch_content += f"Inhalt: {details['body'][:1000]}...\n"

            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        # Speichern
        profile_file.write_text(current_profile, encoding="utf-8")
        return current_profile

    def _get_profiling_prompt(self, email: str, new_content: str, existing_profile: str) -> str:
        """Erstellt den Prompt für das LLM.

        Args:
            email (str): E-Mail-Adresse.
            new_content (str): Neuer E-Mail-Inhalt (Batch).
            existing_profile (str): Bisheriger Steckbrief.

        Returns:
            str: Der formatierte Prompt.
        """
        if not existing_profile:
            context = "Dies ist der Beginn der Analyse. Erstelle einen neuen Steckbrief."
        else:
            context = f"Bisheriger Steckbrief:\n\n{existing_profile}\n\nAktualisiere diesen Steckbrief mit den folgenden neuen Informationen."

        return f"""Du bist ein Assistent, der Personen-Steckbriefe aus E-Mails erstellt.
Die Zielperson hat die E-Mail-Adresse: {email}

{context}

Hier sind die neuen E-Mails:
{new_content}

Erstelle einen strukturierten Steckbrief in Markdown mit folgenden Punkten:
1. Name und E-Mailadresse
2. Rolle (z.B. Studierende, Lehrende, Mitarbeiter, Professor, externer Partner, ...)
3. Datum des ersten Kontakts
4. Wichtige Stationen/Ereignisse:
   - Bei Mitarbeitern: Wichtige Aufgaben, Projekte, Zuständigkeiten.
   - Bei Professoren: Gelesene Module, Forschungsprojekte, Gremienarbeit.
   - Bei Studierenden: Abgeschlossene Projektarbeiten/Thesen, Wechsel der Prüfungsordnung, Praktika, etc.
   - Sonstiges: Alle weiteren relevanten Informationen aus dem Mailverlauf.

Verhalte dich objektiv und sachlich. Antworte NUR mit dem Markdown-Inhalt des Steckbriefs.
"""

    def get_profile(self, email_address: str) -> Optional[str]:
        """Gibt den vorhandenen Steckbrief zurück oder erstellt einen neuen.

        Args:
            email_address (str): E-Mail-Adresse.

        Returns:
            Optional[str]: Steckbrief-Inhalt.
        """
        profile_file = self.storage_path / f"{email_address}.md"
        if profile_file.exists():
            return profile_file.read_text(encoding="utf-8")

        return self.generate_profile(email_address)
