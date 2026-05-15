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
        logger.debug(f"Summarizer initialized with model={model} and base_url={base_url}")

    def summarize_file(self, filename: str, content: str) -> Optional[str]:
        """Erstellt eine strukturierte Zusammenfassung einer einzelnen Datei.

        Extrahiert Dokumenttyp, Thema, Konzepte, Personen und Deadlines.

        Args:
            filename (str): Name der zu zusammenfassenden Datei.
            content (str): Der Textinhalt der Datei.

        Returns:
            Optional[str]: Die generierte Zusammenfassung im Markdown-Format oder None bei Fehlern.
        """
        logger.info(f"Summarizing file: {filename}")

        system_prompt = "You are a university knowledge management assistant. Summarize documents into a structured Markdown format."
        user_prompt = f"""
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
{content[:10000]}
"""
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            logger.debug(f"Sending chat request to Ollama (model={self.model}) for file {filename}")
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0}
            )
            logger.debug(f"Successfully received chat response for file {filename}")
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error summarizing file {filename} with model {self.model}: {e}")
            if "memory" in str(e).lower():
                logger.error("Likely Out of Memory error from Ollama. Check system resources.")
            return None

    def summarize_folder(self, folder_name: str, item_summaries: List[str]) -> Optional[str]:
        """Erstellt eine aggregierte Zusammenfassung für einen Ordner basierend auf Inhalts-Summaries.

        Args:
            folder_name (str): Name des Ordners.
            item_summaries (List[str]): Liste der Zusammenfassungen der enthaltenen Dateien/Unterordner.

        Returns:
            Optional[str]: Die aggregierte Ordner-Zusammenfassung oder None bei Fehlern.
        """
        logger.info(f"Summarizing folder: {folder_name}")
        items_combined = "\n---\n".join(item_summaries)

        system_prompt = "You are a university knowledge management assistant. Create aggregated summaries for folders based on their content."
        user_prompt = f"""
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
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            logger.debug(f"Sending chat request to Ollama (model={self.model}) for folder {folder_name}")
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0}
            )
            logger.debug(f"Successfully received chat response for folder {folder_name}")
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error summarizing folder {folder_name} with model {self.model}: {e}")
            if "memory" in str(e).lower():
                logger.error("Likely Out of Memory error from Ollama. Check system resources.")
            return None

    def answer_question(self, query: str, context: str) -> Optional[str]:
        """Beantwortet eine Frage basierend auf dem bereitgestellten Kontext.

        Args:
            query (str): Die Frage des Nutzers.
            context (str): Der Kontext (z.B. Suchergebnisse).

        Returns:
            Optional[str]: Die generierte Antwort oder None bei Fehlern.
        """
        logger.info(f"Answering question based on context: {query}")

        system_prompt = "You are a university knowledge management assistant. Answer the user's question based ONLY on the provided context. Answer in the same language as the question."
        user_prompt = f"""
Answer the following question based on the provided context from university documents.
If the context does not contain the answer, say that you don't know based on the documents.

Context:
{context}

Question:
{query}

Answer:
"""
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            logger.debug(f"Sending chat request to Ollama (model={self.model}) for question answering")
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0}
            )
            logger.debug("Successfully received chat response for question answering")
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error answering question with model {self.model}: {e}")
            return None
