"""KI-basierte Zusammenfassungs-Engine."""
import ollama
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Summarizer:
    """LLM-basierter Dienst zur Erstellung von Zusammenfassungen für Dateien und Ordner.

    Nutzt Ollama zur Generierung strukturierter Markdown-Zusammenfassungen basierend auf
    vordefinierten Prompts für den universitären Kontext.
    """

    def __init__(self, model: str = "gemma2:2b", base_url: str = "http://localhost:11434"):
        """Initialisiert den Summarizer mit Modellkonfiguration.

        Args:
            model (str): Name des zu verwendenden Ollama-Modells. Defaults to "gemma2:2b".
            base_url (str): Basis-URL des Ollama-API-Servers. Defaults to "http://localhost:11434".
        """
        self.model = model
        self.client = ollama.Client(host=base_url)
        logger.debug(f"Summarizer initialized with model={model} and base_url={base_url}")

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
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
        try:
            response = self.client.chat(model=self.model, messages=messages, options={"temperature": 0})
            doc_type = response['message']['content'].strip()
            logger.debug(f"Identified document type: {doc_type}")
            return doc_type
        except Exception as e:
            logger.error(f"Error identifying document type: {e}")
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
{content[:5000]}
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
{content[:10000]}
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
{content[:15000]}
"""
        return self._chat_request(system_prompt, user_prompt)

    def _chat_request(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Hilfsmethode für Ollama-Chat-Anfragen."""
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0}
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error in chat request: {e}")
            if "memory" in str(e).lower():
                logger.error("Likely Out of Memory error from Ollama.")
            return None

    def summarize_folder(self, folder_name: str, item_summaries: List[str]) -> Optional[str]:
        """Erstellt eine aggregierte Zusammenfassung für einen Ordner auf Deutsch."""
        logger.info(f"Summarizing folder: {folder_name}")
        items_combined = "\n---\n".join(item_summaries)

        system_prompt = "Du bist ein Assistent für universitäres Wissensmanagement. Erstelle Ordner-Zusammenfassungen auf Deutsch."
        user_prompt = f"""
Erstelle eine Zusammenfassung für den Ordner '{folder_name}' basierend auf den Inhalten.

Format:
# Ordner
{folder_name}
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
{items_combined[:15000]}
"""
        return self._chat_request(system_prompt, user_prompt)

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
