"""Module for generating and updating person profiles."""
import email.utils
import json
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
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
        name_part, addr_part = email.utils.parseaddr(email_address)
        actual_email = addr_part.lower() if addr_part else email_address.lower()

        logger.info(f"Suche E-Mails für Adresse: {actual_email} (Input: {email_address})")

        email_address = actual_email
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

                        # Check recipients (To and Cc)
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
                                "date": details.get("date", datetime.min),
                                "details": details
                            })
                    except Exception as e:
                        logger.warning(f"Fehler beim Parsen von {file_path}: {e}")

        # Sortieren nach Datum absteigend, um die neuesten 100 zu nehmen
        found_emails.sort(key=lambda x: x["date"], reverse=True)
        return found_emails[:100]

    def create_batches(self, emails: List[Dict[str, Any]], max_chars: int = 15000) -> List[List[Dict[str, Any]]]:
        """Teilt E-Mails in Batches auf, um die Kontextgröße des LLM nicht zu überschreiten.

        Args:
            emails (List[Dict[str, Any]]): Liste der E-Mails.
            max_chars (int): Maximale Zeichenanzahl pro Batch.

        Returns:
            List[List[Dict[str, Any]]]: Liste von E-Mail-Batches.
        """
        # Sortieren nach Datum
        emails.sort(key=lambda x: x["details"]["date"])

        batches = []
        current_batch = []
        current_chars = 0

        for mail in emails:
            mail_chars = len(mail["details"]["body"])
            if current_chars + mail_chars > max_chars and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

            current_batch.append(mail)
            current_chars += mail_chars

        if current_batch:
            batches.append(current_batch)

        # Größte zeitliche Lücke finden für intelligentes Batching
        if len(batches) > 1:
            return self._optimize_batches(batches)

        return batches

    def _optimize_batches(self, batches: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Optimiert Batches basierend auf zeitlichen Abständen.

        Wenn zwischen zwei E-Mails eine große Pause liegt (z.B. Semesterferien),
        sollte dort ein Batch-Schnitt erfolgen.

        Args:
            batches (List[List[Dict[str, Any]]]): Vorläufige Batches.

        Returns:
            List[List[Dict[str, Any]]]: Optimierte Batches.
        """
        all_emails = [mail for batch in batches for mail in batch]
        if len(all_emails) < 2:
            return batches

        gaps = []
        for i in range(len(all_emails) - 1):
            val1 = all_emails[i]["details"]["date"]
            d1 = val1 if isinstance(val1, datetime) else datetime.fromisoformat(val1.replace("Z", "+00:00"))
            val2 = all_emails[i+1]["details"]["date"]
            d2 = val2 if isinstance(val2, datetime) else datetime.fromisoformat(val2.replace("Z", "+00:00"))
            gaps.append((d2 - d1).total_seconds())

        if not gaps:
            return batches

        # Top-Gaps finden (einfacher Ansatz: alles über dem Durchschnitt * 2)
        avg_gap = sum(gaps) / len(gaps)
        threshold = max(avg_gap * 2, 60 * 60 * 24 * 30) # Mindestens 30 Tage

        optimized_batches = []
        current_batch = [all_emails[0]]

        for i in range(len(all_emails) - 1):
            if gaps[i] > threshold:
                optimized_batches.append(current_batch)
                current_batch = []
            current_batch.append(all_emails[i+1])

        if current_batch:
            optimized_batches.append(current_batch)

        # Falls ein Batch immer noch zu groß ist, rekursiv splitten (einfaches Halbier-Prinzip)
        final_batches = []
        for batch in optimized_batches:
            batch_chars = sum(len(m["details"]["body"]) for m in batch)
            if batch_chars > 20000:
                split_idx = len(batch) // 2
                final_batches.append(batch[:split_idx])
                final_batches.append(batch[split_idx:])
            else:
                final_batches.append(batch)

        return final_batches

    def _get_knowledge_graph_context(self, email_address: str) -> str:
        """Sucht im Wissensgraphen nach Informationen über die Person.

        Verfolgt ausgehende Kanten mittels Tiefensuche (DFS), um Fakultät, Institut etc. zu finden.

        Args:
            email_address (str): E-Mail-Adresse der Person.

        Returns:
            str: Formatierte Informationen aus dem Wissensgraphen.
        """
        name_part, addr_part = email.utils.parseaddr(email_address)
        actual_email = addr_part.lower() if addr_part else email_address.lower()

        logger.info(f"Suche im Wissensgraph für: {actual_email} (Name: {name_part})")

        person_node = self.store.get_node_by_property("email", actual_email)

        # Fallback: Suche nach Name, falls im Adress-String vorhanden
        if not person_node and name_part:
            logger.info(f"Kein Knoten für Email {actual_email} gefunden. Versuche Suche nach Name: {name_part}")
            # Wir suchen hier nach dem exakten Namen oder Varianten ("Vorname Nachname" vs "Nachname, Vorname")
            name_variants = [name_part]
            if " " in name_part and "," not in name_part:
                parts = name_part.split(" ")
                name_variants.append(f"{parts[-1]}, {' '.join(parts[:-1])}")

            for node in self.store.get_all_nodes():
                if node.get("type") == "Person":
                    node_name = node.get("name", "")
                    if node_name in name_variants:
                        person_node = node
                        logger.info(f"Person über Name {node_name} gefunden.")
                        break

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
        logger.info(f"generate_profile aufgerufen für: {email_address} (force_update={force_update})")

        name_part, addr_part = email.utils.parseaddr(email_address)
        actual_email = addr_part.lower() if addr_part else email_address.lower()

        profile_file = self.storage_path / f"{actual_email}.md"

        if profile_file.exists() and not force_update:
            logger.info(f"Steckbrief für {email_address} existiert bereits.")
            return profile_file.read_text(encoding="utf-8")

        is_tool_user = email_address.lower() in [e.lower() for e in self.config.user.emails]
        emails = [] if is_tool_user else self.find_emails_for_address(email_address)
        kg_context = self._get_knowledge_graph_context(email_address)

        if is_tool_user:
            user_info = f"Informationen aus der Konfiguration (user.yaml):\n- Name: {self.config.user.name}\n- E-Mail: {self.config.user.email}\n"
            kg_context = user_info + kg_context

        if not emails and not kg_context:
            logger.warning(f"Keine E-Mails und keine Wissensgraph-Infos für {actual_email} (Input: {email_address}) gefunden.")
            return None

        batches = self.create_batches(emails) if emails else [[]]
        current_profile = ""
        honorific = self._determine_honorific(emails)

        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\n"
                batch_content += f"Betreff: {details['subject']}\n"
                batch_content += f"Inhalt: {details['body'][:1000]}...\n"

            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, honorific, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        # Quellen hinzufügen
        sources_text = self._get_sources_text(emails, kg_context)
        current_profile += sources_text

        # Speichern
        profile_file.write_text(current_profile, encoding="utf-8")
        
        # Tracking aktualisieren
        if emails:
            filenames = [m["path"].name for m in emails]
            self.profile_store.add_processed_emails(email_address, filenames)

        return current_profile

    def update_profile(self, email_address: str) -> Optional[str]:
        """Aktualisiert den Steckbrief einer Person, falls neue E-Mails vorhanden sind.

        Dabei werden nur E-Mails berücksichtigt, die sowohl noch nicht in der Tracking-Datenbank
        erfasst sind als auch ein neueres Datum als die Steckbrief-Datei selbst haben.

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

        is_tool_user = email_address.lower() in [e.lower() for e in self.config.user.emails]
        if is_tool_user:
            # Für den Tool-Nutzer aktualisieren wir immer aus dem KG (einfach neu generieren)
            return self.generate_profile(email_address, force_update=True)

        existing_profile = profile_file.read_text(encoding="utf-8")

        # Bestimme das Alter des aktuellen Steckbriefs
        profile_mtime = datetime.fromtimestamp(profile_file.stat().st_mtime, tz=timezone.utc)

        # Bestehende Quellen entfernen, damit sie nicht in den Prompt gelangen
        if "## Quellen" in existing_profile:
            existing_profile = existing_profile.split("## Quellen")[0].strip()

        processed_files = self.profile_store.get_processed_filenames(email_address)
        
        all_emails = self.find_emails_for_address(email_address)

        # Filtern:
        # 1. Nicht bereits verarbeitet (Tracking DB)
        # 2. Datum der Mail ist neuer als die Steckbrief-Datei
        new_emails = []
        for m in all_emails:
            if m["path"].name in processed_files:
                continue

            # Das Datum kann direkt im Dictionary oder in 'details' liegen
            mail_date = m.get("date") or m.get("details", {}).get("date")

            if not isinstance(mail_date, datetime):
                try:
                    mail_date = datetime.fromisoformat(str(mail_date).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    mail_date = datetime.min.replace(tzinfo=timezone.utc)

            if mail_date.tzinfo is None:
                mail_date = mail_date.replace(tzinfo=timezone.utc)

            if mail_date > profile_mtime:
                new_emails.append(m)

        if not new_emails:
            logger.info(f"Keine neuen E-Mails für {email_address} nach dem {profile_mtime} gefunden.")
            return existing_profile

        logger.info(f"{len(new_emails)} neue E-Mails für {email_address} nach dem {profile_mtime} gefunden. Aktualisiere Steckbrief...")
        
        kg_context = self._get_knowledge_graph_context(email_address)
        batches = self.create_batches(new_emails)
        current_profile = existing_profile
        honorific = self._determine_honorific(all_emails)

        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Update-Batch {i+1}/{len(batches)} für {email_address}")
            batch_content = ""
            for mail in batch:
                details = mail["details"]
                batch_content += f"\n--- Datum: {details['date']} ---\n"
                batch_content += f"Betreff: {details['subject']}\n"
                batch_content += f"Inhalt: {details['body'][:1000]}...\n"

            prompt = self._get_profiling_prompt(email_address, batch_content, current_profile, honorific, kg_context)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            current_profile = response["message"]["content"]

        # Quellen hinzufügen (basierend auf allen E-Mails)
        sources_text = self._get_sources_text(all_emails, kg_context)
        current_profile += sources_text

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

    def _determine_honorific(self, emails: List[Dict[str, Any]]) -> str:
        """Bestimmt die bevorzugte Anrede (Du/Sie) basierend auf den 3 neuesten E-Mails.

        Args:
            emails (List[Dict[str, Any]]): Liste der E-Mails.

        Returns:
            str: "Du" oder "Sie".
        """
        if not emails:
            return "Sie"

        # Sortieren nach Datum absteigend und die neuesten 3 nehmen
        # Wir schauen sowohl in 'date' (für find_emails_for_address Ergebnisse)
        # als auch in 'details'['date'] (für Batch-Inhalte)
        def get_date(m):
            """Hilfsfunktion zum Auslesen des Datums."""
            if "date" in m:
                return m["date"]
            return m["details"].get("date", datetime.min)

        sorted_emails = sorted(emails, key=get_date, reverse=True)
        latest_emails = sorted_emails[:3]

        for mail in latest_emails:
            details = mail.get("details", mail)
            body = details.get("body", "")
            subject = details.get("subject", "")

            prompt = f"""Analysiere die folgende E-Mail und bestimme, ob die Person mit "Du" oder "Sie" angesprochen wird (oder selbst "Du" oder "Sie" verwendet).
Betreff: {subject}
Inhalt: {body[:1000]}

Antworte NUR mit "Du", "Sie" oder "Unklar".
"""
            try:
                response = self.llm.chat([{"role": "user", "content": prompt}])
                res = response["message"]["content"].strip().lower()
                if "du" in res:
                    return "Du"
                if "sie" in res:
                    return "Sie"
            except Exception as e:
                logger.warning(f"Fehler bei der Honorific-Bestimmung für eine Mail: {e}")

        return "Sie"

    def _get_sources_text(self, emails: List[Dict[str, Any]], kg_context: str) -> str:
        """Erstellt den Text für den Quellen-Abschnitt.

        Args:
            emails (List[Dict[str, Any]]): Liste der E-Mails.
            kg_context (str): Kontext aus dem Wissensgraphen.

        Returns:
            str: Formatierter Quellen-Text.
        """
        sources = []
        if kg_context:
            sources.append("- Wissensgraph")

        folders = set()
        for mail in emails:
            path = Path(mail["path"])
            folders.add(str(path.parent))

        for folder in sorted(list(folders)):
            sources.append(f"- Ordner: {folder}")

        if not sources:
            return ""

        return "\n\n## Quellen\n" + "\n".join(sources) + "\n"

    def _get_profiling_prompt(self, email: str, new_content: str, existing_profile: str, honorific_preference: str, kg_context: str = "") -> str:
        """Erstellt den Prompt für das LLM.

        Args:
            email (str): E-Mail-Adresse.
            new_content (str): Neuer E-Mail-Inhalt (Batch).
            existing_profile (str): Bisheriger Steckbrief.
            honorific_preference (str): Vorab bestimmte Anrede (Du/Sie).
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

Falls die E-Mailadresse NICHT "th-koeln" enthält, handelt es sich um eine externe Person. In diesem Fall ergänze bitte (falls in den Mails vorhanden):
- Name des Unternehmens
- Kontaktdaten (Telefon, Adresse, etc.)
- Branche des Unternehmens

Erstelle einen strukturierten Steckbrief in Markdown mit folgenden Punkten:
1. Name und E-Mailadresse
2. Rolle (z.B. Studierende, Lehrende, Mitarbeiter, Professor, externer Partner, ...)
3. Bevorzugte Anrede (Setze hier zwingend den Wert: {honorific_preference})
4. Datum des ersten Kontakts
5. Bei externen Personen: Unternehmensname, Branche und Kontaktdaten (falls bekannt)
6. Wichtige Stationen/Ereignisse:
   - Bei Mitarbeitern: Wichtige Aufgaben, Projekte, Zuständigkeiten.
   - Bei Professoren: Gelesene Module, Forschungsprojekte, Gremienarbeit.
   - Bei Studierenden: Abgeschlossene Projektarbeiten/Thesen, Wechsel der Prüfungsordnung, Praktika, etc.
   - Sonstiges: Alle weiteren relevanten Informationen aus dem Mailverlauf.

WICHTIG: Erstelle KEINEN Abschnitt "Quellen". Dieser wird automatisch generiert.

Verhalte dich objektiv und sachlich. Antworte NUR with dem Markdown-Inhalt des Steckbriefs.
"""
