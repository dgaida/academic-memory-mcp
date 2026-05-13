import logging
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SearchIndex:
    """Schnittstelle zum qmd-basierten Suchindex.

    Ermöglicht die hybride Suche (semantisch und Schlüsselwort) über die Dokumentensammlung.
    """

    def __init__(self, location: str, embedding_model_name: str = "BAAI/bge-m3"):
        """Initialisiert den SearchIndex.

        Args:
            location (str): Pfad zum Speicherort des Index.
            embedding_model_name (str): Name des zu verwendenden Embedding-Modells. Defaults to "BAAI/bge-m3".
        """
        self.location = location
        logger.info(f"Initializing SearchIndex with qmd backend (location: {location})")

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Fügt ein Dokument zum Index hinzu.

        Hinweis: In der aktuellen Implementierung erfolgt die Indexierung primär über den
        externen qmd-Prozess während des Crawlings.

        Args:
            doc_id (str): Eindeutige ID des Dokuments (Pfad).
            content (str): Textinhalt des Dokuments.
            metadata (Dict[str, Any]): Metadaten zum Dokument.
        """
        pass

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Führt eine hybride Suche im Index aus.

        Ruft das externe 'qmd'-Tool auf und parst die JSON-Ergebnisse.

        Args:
            query (str): Die Suchanfrage.
            top_k (int): Anzahl der zurückzugebenden Ergebnisse. Defaults to 5.

        Returns:
            List[Dict[str, Any]]: Liste der Suchergebnisse mit Pfad, Inhalt und Score.
        """
        try:
            result = subprocess.run([
                "qmd", "query", query, "--json", "-n", str(top_k)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                result = subprocess.run([
                    "qmd", "search", query, "--json", "-n", str(top_k)
                ], capture_output=True, text=True)

            if result.returncode == 0:
                # Extract JSON from output (might contain noise from node-llama-cpp build attempts)
                stdout = result.stdout
                match = re.search(r'\[\s*\{.*\}\s*\]', stdout, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    try:
                        qmd_results = json.loads(json_str)
                        formatted_results = []
                        for res in qmd_results:
                            path = res.get("file", "")
                            formatted_results.append({
                                "path": path,
                                "content": res.get("snippet", ""),
                                "filename": res.get("title", ""),
                                "score": res.get("score", 0),
                                "metadata": res
                            })
                        return formatted_results
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode extracted JSON: {json_str}")
                else:
                    logger.error(f"No JSON found in qmd output: {stdout}")
            else:
                logger.error(f"qmd search failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error during qmd search: {e}")

        return []
