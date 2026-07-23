"""Modul zum automatisierten Lernen von Aliassen (Ontologie) aus E-Mails und Metadaten."""
import logging
import re
from pathlib import Path
from typing import Dict, Set
from mcp_university.metadata.store import MetadataStore
from academic_parser.mail_parser import MailParser
from mcp_university.summarizer.engine import Summarizer

logger = logging.getLogger(__name__)

class OntologyLearner:
    """Lernt Alias-Beziehungen für Personen und Module."""

    def __init__(self, store: MetadataStore, summarizer: Summarizer) -> None:
        """Initialisiert den OntologyLearner.

        Args:
            store (MetadataStore): Metadatenspeicher für den Graphen.
            summarizer (Summarizer): LLM Summarizer.
        """
        self.store = store
        self.summarizer = summarizer
        self.mail_parser = MailParser()

    def learn_from_emails(self, base_path: Path) -> None:
        """Scannt E-Mails nach Name-Email-Paaren, um Personen-Aliase zu finden."""
        logger.info(f"Starte Personen-Ontologie-Lernen in {base_path}...")
        email_to_names: Dict[str, Set[str]] = {}

        # Alle .msg und .eml Dateien finden
        for mail_file in list(base_path.rglob("*.msg")) + list(base_path.rglob("*.eml")):
            try:
                # Wir brauchen hier nur den Header, MailParser.parse liefert ihn
                content = self.mail_parser.parse(mail_file)
                if not content:
                    continue

                # Extrahiere "From: Name <email>" oder "From: email"
                # Wir suchen nach Zeilen wie "From: Daniel Gaida <daniel.gaida@th-koeln.de>"
                # oder "From: daniel.gaida@th-koeln.de"
                match = re.search(r"From:\s*(.*?)\s*<(.*?)>", content)
                if match:
                    name = match.group(1).strip().strip('"').strip("'")
                    email = match.group(2).strip().lower()
                    if name and email:
                        if email not in email_to_names:
                            email_to_names[email] = set()
                        email_to_names[email].add(name)
                else:
                    # Fallback für nur E-Mail
                    match_email = re.search(r"From:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", content)
                    if match_email:
                        email = match_email.group(1).strip().lower()
                        # Hier haben wir keinen Namen, ignorieren wir für Aliase
            except Exception as e:
                logger.debug(f"Fehler beim Verarbeiten von {mail_file} für Ontologie: {e}")

        # Aliase in die DB schreiben
        for email, names in email_to_names.items():
            if len(names) > 1:
                # Wähle den längsten Namen als kanonisch (Heuristik)
                sorted_names = sorted(list(names), key=len, reverse=True)
                canonical_name = sorted_names[0]
                for alias in sorted_names[1:]:
                    logger.info(f"Neuer Alias gefunden: {alias} -> {canonical_name} (Email: {email})")
                    self.store.add_alias(alias, canonical_name, "Person")

    def learn_module_aliases(self) -> None:
        """Nutzt das LLM, um Modul-Aliase aus den vorhandenen Knoten zu finden."""
        logger.info("Starte Modul-Ontologie-Lernen mittels LLM...")
        nodes = self.store.get_all_nodes()
        modules = [n['name'] for n in nodes if n['type'] == 'Modul']

        if len(modules) < 2:
            return

        system_prompt = """Du bist ein Experte für universitäre Ontologien. Deine Aufgabe ist es, unterschiedliche Schreibweisen für dieselben Module zu finden.
Beispiele: ("KI", "Künstliche Intelligenz"), ("Algorithmen & Datenstrukturen", "ALDA").

Antworte NUR mit einer JSON-Liste von Paaren [alias, canonical_name].
"""
        user_prompt = f"Finde Duplikate/Aliase in dieser Liste von Modulnamen:\n{modules}"

        response = self.summarizer._chat_request(system_prompt, user_prompt)
        if not response:
            return

        try:
            import json
            # Versuche JSON zu finden
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                pairs = json.loads(response[start_idx:end_idx])
                for pair in pairs:
                    if isinstance(pair, list) and len(pair) == 2:
                        alias, canonical = pair
                        logger.info(f"Neuer Modul-Alias gefunden: {alias} -> {canonical}")
                        self.store.add_alias(alias, canonical, "Modul")
        except Exception as e:
            logger.error(f"Fehler beim Parsen der Modul-Aliase: {e}")
