"""KI-basierte Zusammenfassungs-Engine."""
import ollama
from typing import Optional, List
import logging

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

    def summarize_file(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine strukturierte Zusammenfassung einer einzelnen Datei.

        Extrahiert Dokumenttyp, Thema, Konzepte, Personen und Deadlines.

        Args:
            filename (str): Name der zu zusammenfassenden Datei.
            content (str): Der Textinhalt der Datei.

        Returns:
            Optional[str]: Die generierte Zusammenfassung im Markdown-Format oder None bei Fehlern.
        """
        prompt = f"""
Summarize the following document for a university knowledge system.
Filename: {filename}

Provide the summary in the following Markdown format:
# Datei
{filename}
# Dokumenttyp
(Identify the type of document)
# Thema
(Core topic)
# Kurzfassung
(Concise summary)
# Wichtige Konzepte
- concept 1
- ...
# Beteiligte Personen
- Name 1
- ...
# Deadlines
- YYYY-MM-DD: Description
# Relevanz
(Why is this important?)

Document Content:
{content[:10000]} # Limiting content to avoid context window issues
"""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0}
            )
            return response['response']
        except Exception as e:
            logger.error(f"Error summarizing file {filename}: {e}")
            return None

    def summarize_folder(self, folder_name: str, item_summaries: List[str]) -> Optional[str]:
        """Erstellt eine aggregierte Zusammenfassung für einen Ordner basierend auf Inhalts-Summaries.

        Args:
            folder_name (str): Name des Ordners.
            item_summaries (List[str]): Liste der Zusammenfassungen der enthaltenen Dateien/Unterordner.

        Returns:
            Optional[str]: Die aggregierte Ordner-Zusammenfassung oder None bei Fehlern.
        """
        items_combined = "\n---\n".join(item_summaries)
        prompt = f"""
Create a summary for the folder '{folder_name}' based on the summaries of its contents.

Format:
# Ordner
{folder_name}
# Typ
(e.g., Student Record, Course Material, Research Project)
# Thema
(Overall theme)
# Aktueller Status
(Summary of progress if applicable)
# Offene Aufgaben
- task 1
- ...
# Wichtige Dokumente
- doc 1
- ...
# Zusammenfassung
(High-level overview)

Contents:
{items_combined[:15000]}
"""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0}
            )
            return response['response']
        except Exception as e:
            logger.error(f"Error summarizing folder {folder_name}: {e}")
            return None
