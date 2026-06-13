"""KI-basierte Zusammenfassungs-Engine."""
from typing import Optional, List
import logging
from pathlib import Path
from ..utils.llm_client_wrapper import LLMClientWrapper

logger = logging.getLogger(__name__)

class Summarizer:
    """LLM-basierter Dienst zur Erstellung von Zusammenfassungen für Dateien und Ordner.

    Nutzt LLMClientWrapper zur Generierung strukturierter Markdown-Zusammenfassungen basierend auf
    vordefinierten Prompts für den universitären Kontext.
    """

    def __init__(self, model: str = None, base_url: str = None) -> None:
        """Initialisiert den Summarizer mit Modellkonfiguration.

        Args:
            model (str, optional): Name des zu verwendenden Modells.
            base_url (str, optional): Basis-URL des API-Servers.
        """
        self.client = LLMClientWrapper(model=model, base_url=base_url)
        self.model = self.client.model
        logger.debug(f"Summarizer initialized with model={self.model}")

    def _identify_document_type(self, content: str) -> str:
        """Identifiziert den Dokumenttyp basierend auf dem Inhalt des Dokuments (erste Seite/Anfang).

        Args:
            content (str): Der Textinhalt des Dokuments.

        Returns:
            str: Der identifizierte Dokumenttyp.
        """
        system_prompt = "Du bist ein Assistent zur Dokumentenanalyse. Identifiziere den Typ des Dokuments basierend auf dem Textanfang."
        user_prompt = f"""Analysiere den folgenden Textanfang und entscheide, um welche Art von Dokument es sich handelt (z.B. Abschlussarbeit, Protokoll, Formular, Prüfungsordnung, Vorlesungsskript, Übungsblatt, Sonstiges).
Antworte NUR mit dem Typ des Dokuments.

Textanfang:
{content[:2000]}
"""
        doc_type = self._chat_request(system_prompt, user_prompt)
        if doc_type:
            doc_type = doc_type.strip()
            logger.debug(f"Identified document type: {doc_type}")
            return doc_type
        return "Unbekannt"

    def summarize_file(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine strukturierte Zusammenfassung einer einzelnen Datei.

        Wählt die passende Zusammenfassungsstrategie basierend auf dem Dateityp.

        Args:
            filename (str): Name der zu zusammenfassenden Datei.
            content (str): Der Textinhalt der Datei.

        Returns:
            Optional[str]: Die generierte Zusammenfassung im Markdown-Format oder None bei Fehlern.
        """
        suffix = Path(filename).suffix.lower()
        if suffix in [".msg", ".eml"]:
            return self._summarize_email(filename, content)
        elif suffix in [".pdf", ".docx"]:
            return self._summarize_long_doc(filename, content)
        else:
            return self._summarize_short_doc(filename, content)

    def _summarize_email(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine Zusammenfassung für eine E-Mail."""
        logger.info(f"Summarizing email: {filename}")
        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Erstelle Zusammenfassungen von E-Mails auf Deutsch."
        user_prompt = f"""Fasse die folgende E-Mail kurz und präzise zusammen.
Dateiname: {filename}

Format:
# E-Mail Zusammenfassung
{filename}
# Absender & Empfänger
(Wer schreibt an wen?)
# Betreff
(Thema der E-Mail)
# Kernaussage
(Zusammenfassung des Inhalts)
# Aufgaben/Aktionen
- Aufgabe 1
- ...
# Wichtige Termine/Deadlines
- YYYY-MM-DD: Beschreibung

Inhalt:
{content[:10000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def _summarize_short_doc(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine Zusammenfassung für kurze Dokumente (Markdown, Text, etc.)."""
        logger.info(f"Summarizing short document: {filename}")
        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Erstelle Zusammenfassungen von Dokumenten auf Deutsch."
        user_prompt = f"""Erstelle eine strukturierte Zusammenfassung für das folgende Dokument.
Dateiname: {filename}

Format:
# Datei
{filename}
# Dokumenttyp
(z.B. Notizen, Skript, Code)
# Thema
(Hauptthema)
# Kurzfassung
(Prägnante Zusammenfassung)
# Wichtige Punkte
- Punkt 1
- ...

Dokumentinhalt:
{content[:20000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def _summarize_long_doc(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine Zusammenfassung für lange Dokumente (PDF, DOCX)."""
        logger.info(f"Summarizing long document: {filename}")
        doc_type = self._identify_document_type(content)

        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Erstelle detaillierte Zusammenfassungen auf Deutsch."
        user_prompt = f"""Erstelle eine ausführliche Zusammenfassung für dieses {doc_type}.
Dateiname: {filename}

Format:
# Dokument
{filename}
# Typ
{doc_type}
# Zusammenfassung
(Zentrale Inhalte des Dokuments)
# Wichtige Konzepte & Begriffe
- Begriff 1: Erklärung
- ...
# Beteiligte Personen/Institutionen
- Name 1
- ...
# Fristen & Termine
- YYYY-MM-DD: Beschreibung
# Relevanz
(Warum ist dieses Dokument wichtig?)

Inhalt:
{content[:30000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def _chat_request(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Hilfsmethode für LLM-Chat-Anfragen."""
        messages = [
            {'role': 'user', 'content': user_prompt}
        ]
        try:
            response = self.client.chat(
                messages=messages,
                system_prompt=system_prompt
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error in chat request: {e}")
            if "memory" in str(e).lower():
                logger.error("Likely Out of Memory error from LLM.")
            return None

    def summarize_folder(self, folder_name: str, item_summaries: List[str]) -> Optional[str]:
        """Erstellt eine aggregierte Zusammenfassung für einen Ordner auf Deutsch."""
        logger.info(f"Summarizing folder: {folder_name}")
        items_combined = "\n---\n".join(item_summaries)

        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Erstelle Ordner-Zusammenfassungen auf Deutsch."
        user_prompt = f"""
Erstelle eine Zusammenfassung für den Ordner '{folder_name}' basierend auf den Inhalten.
Beachte, dass der Name den Pfad relativ zum Hauptverzeichnis darstellt.

Format:
# Ordner: {folder_name}
# Typ
(z.B. Studierendenakte, Kursmaterialien, Forschungsprojekt)
# Hauptthema
(Übergreifendes Thema)
# Status
(Zusammenfassung des Fortschritts falls relevant)
# Offene Aufgaben
- Aufgabe 1
- ...
# Wichtige Dokumente
- Dokument 1
- ...
# Gesamtübersicht
(High-level Zusammenfassung)

Inhalte:
{items_combined[:40000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def summarize_email_conversation(self, folder_name: str, conversation_content: str) -> Optional[str]:
        """Erstellt eine Zusammenfassung eines E-Mail-Schriftverkehrs (Inbox & SentItems)."""
        logger.info(f"Summarizing email conversation in folder: {folder_name}")

        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Analysiere den E-Mail-Schriftverkehr auf Deutsch."
        user_prompt = f"""Analysiere den folgenden chronologischen E-Mail-Schriftverkehr aus dem Ordner '{folder_name}'.
Beachte, dass der Name den Pfad relativ zum Hauptverzeichnis darstellt.
Ermittle die wichtigsten Informationen und identifiziere noch offene Punkte.
Beachte dabei besonders, ob offene Punkte aus eingehenden Mails (Inbox) bereits durch Antworten (SentItems) erledigt wurden.

Format:
# Ordner: {folder_name} (Zusammenfassung des Schriftverkehrs)
# Beteiligte Personen
- Name 1 (Rolle, falls ersichtlich)
# Hauptthemen & Kontext
(Worum geht es in diesem Austausch?)
# Chronologischer Verlauf
(Kurze Zusammenfassung der wichtigsten Etappen)
# Offene Punkte & Next Steps
- [ ] Punkt 1 (Was ist noch zu tun?)
# Erledigte Punkte
- [x] Punkt A (Was wurde bereits geklärt/beantwortet?)
# Wichtige Termine & Fristen
- YYYY-MM-DD: Beschreibung

Schriftverkehr:
{conversation_content[:50000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def determine_gender(self, first_name: str) -> str:
        """Bestimmt die formale deutsche Anrede (Herr/Frau) basierend auf dem Vornamen mittels LLM.

        Args:
            first_name (str): Der Vorname der Person.

        Returns:
            str: "Herr", "Frau" oder "Herr/Frau".
        """
        logger.info(f"Determining gender for name: {first_name}")
        system_prompt = "Du bist ein Assistent zur Namensanalyse. Bestimme die formale deutsche Anrede (Herr oder Frau) für den gegebenen Vornamen."
        user_prompt = f"Bestimme die Anrede für den Vornamen '{first_name}'. Antworte NUR mit 'Herr', 'Frau' oder 'Herr/Frau', wenn es nicht eindeutig ist."

        result = self._chat_request(system_prompt, user_prompt)
        if not result:
            return "Herr/Frau"

        result = result.strip().replace(".", "")
        if "Frau" in result and "Herr" in result:
            return "Herr/Frau"
        elif "Frau" in result:
            return "Frau"
        elif "Herr" in result:
            return "Herr"
        return "Herr/Frau"

    def answer_question(self, query: str, context: str) -> Optional[str]:
        """Beantwortet eine Frage basierend auf dem Kontext auf Deutsch."""
        logger.info(f"Answering question: {query}")

        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Beantworte die Frage des Nutzers NUR basierend auf dem bereitgestellten Kontext. Antworte in der Sprache der Frage (standardmäßig Deutsch)."
        user_prompt = f"""
Beantworte die folgende Frage basierend auf dem bereitgestellten Kontext aus Universitätsdokumenten.
Falls der Kontext die Antwort nicht enthält, sage dass du es basierend auf den Dokumenten nicht weißt.

Kontext:
{context}

Frage:
{query}

Antwort:
"""
        return self._chat_request(system_prompt, user_prompt)
