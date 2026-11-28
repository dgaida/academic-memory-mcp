"""Skript zum Aufbau des semantischen E-Mail-Vektorindex.

Durchläuft alle konfigurierten E-Mail-Ordner, liest den JSON-Index der
``EmailSearchEngine`` ein und erzeugt für jede noch nicht indizierte Mail
ein Embedding über das Ollama-Modell ``embeddinggemma-2:270m``. Die
Embedding-Vektoren werden in einer lokalen Qdrant-Datenbank gespeichert.

Verwendung::

    python scripts/build_semantic_email_index.py [--force] [--batch-size 32]
"""

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from academic_parser.mail_parser import MailParser
from mcp_university.config import get_config
from mcp_university.utils.email_search import EmailSearchEngine
from mcp_university.utils.semantic_email_search import (
    DEFAULT_SEMANTIC_MODEL,
    SemanticEmailSearchEngine,
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("build_semantic_email_index")


def _load_body_preview(file_path: str, parser: MailParser, max_chars: int = 500) -> str:
    """Liest die ersten Zeichen des E-Mail-Bodys für das Embedding.

    Args:
        file_path (str): Absoluter Pfad zur .msg- oder .eml-Datei.
        parser (MailParser): Instanz des MailParsers.
        max_chars (int): Maximale Zeichenanzahl des Body-Vorschau.

    Returns:
        str: Gekürzter Mailinhalt oder leerer String bei Fehler.
    """
    try:
        content = parser.parse(Path(file_path))
        if content:
            return content[:max_chars]
    except Exception as exc:
        logger.debug(f"Body-Vorschau für {file_path} nicht abrufbar: {exc}")
    return ""


def build_index(
    force: bool = False,
    batch_size: int = 32,
    ollama_base_url: Optional[str] = None,
    embedding_model: str = DEFAULT_SEMANTIC_MODEL,
    store_dir: Optional[Path] = None,
) -> None:
    """Erstellt oder aktualisiert den semantischen Vektorindex für alle E-Mails.

    Args:
        force (bool): Falls True, werden alle Mails neu indiziert.
        batch_size (int): Anzahl der E-Mails pro Ollama-Anfrage.
        ollama_base_url (Optional[str]): Basis-URL des Ollama-Servers.
        embedding_model (str): Ollama-Modellname für die Embeddings.
        store_dir (Optional[Path]): Zielverzeichnis für den Qdrant-Store.

    Returns:
        None
    """
    cfg = get_config()

    # 1. JSON-Index der EmailSearchEngine laden (Metadaten ohne Body)
    logger.info("Lade EmailSearchEngine-Index …")
    search_engine = EmailSearchEngine()
    if not search_engine.index:
        logger.info("Index ist leer — starte Update …")
        search_engine.update_index()

    all_mails: List[Dict[str, Any]] = search_engine.index
    logger.info(f"{len(all_mails)} E-Mails im Text-Index gefunden.")

    # 2. Semantische Such-Engine initialisieren
    sem_engine = SemanticEmailSearchEngine(
        store_dir=store_dir,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url or str(cfg.llm.base_url),
        batch_size=batch_size,
    )

    # 3. Veraltete Einträge entfernen (nur wenn kein force-Rebuild)
    if not force and sem_engine.indexed_count > 0:
        existing_paths = [m["path"] for m in all_mails]
        removed = sem_engine.remove_missing(existing_paths)
        if removed:
            logger.info(f"{removed} nicht mehr vorhandene Mails aus Index entfernt.")

    # 4. Ausstehende Mails bestimmen
    if force:
        mails_to_index = all_mails
        logger.info(f"Force-Modus: alle {len(mails_to_index)} Mails werden neu indiziert.")
    else:
        mails_to_index = [m for m in all_mails if not sem_engine.is_indexed(m["path"])]
        logger.info(
            f"{len(mails_to_index)} neue / fehlende Mails werden indiziert "
            f"({sem_engine.indexed_count} bereits vorhanden)."
        )

    if not mails_to_index:
        logger.info("Kein Update notwendig — Index ist aktuell.")
        return

    # 5. Body-Vorschau für das Embedding nachladen
    mail_parser = MailParser()
    logger.info("Lade Body-Vorschau für Embeddings …")
    enriched: List[Dict[str, Any]] = []
    for mail in mails_to_index:
        body_preview = _load_body_preview(mail["path"], mail_parser)
        enriched.append({**mail, "body_preview": body_preview})

    # 6. Batches in den semantischen Index schreiben
    total = len(enriched)
    logger.info(f"Starte Indexierung von {total} Mails in Batches à {batch_size} …")
    for start in range(0, total, batch_size * 4):  # Makro-Batches für Log-Fortschritt
        chunk = enriched[start : start + batch_size * 4]
        sem_engine.upsert_emails(chunk)
        done = min(start + batch_size * 4, total)
        logger.info(f"  Fortschritt: {done}/{total} Mails indiziert …")

    logger.info(
        f"Semantischer Vektorindex vollständig aufgebaut: "
        f"{sem_engine.indexed_count} Einträge in {sem_engine.store_dir}."
    )


def main() -> None:
    """Einstiegspunkt des Skripts.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description=(
            "Erstellt den semantischen E-Mail-Vektorindex mit "
            f"Ollama '{DEFAULT_SEMANTIC_MODEL}'."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Kompletter Neuaufbau des Index (alle Mails neu einlesen).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Anzahl der E-Mails pro Ollama-Embedding-Anfrage (default: 32).",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=DEFAULT_SEMANTIC_MODEL,
        help=f"Ollama-Modellname (default: {DEFAULT_SEMANTIC_MODEL}).",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=None,
        help="Ollama-Server-URL (default: aus models.yaml).",
    )
    parser.add_argument(
        "--store-dir",
        type=str,
        default=None,
        help="Pfad zum Qdrant-Speicherverzeichnis (default: data/semantic_email_index/).",
    )
    args = parser.parse_args()

    store_dir = Path(args.store_dir) if args.store_dir else None
    build_index(
        force=args.force,
        batch_size=args.batch_size,
        ollama_base_url=args.ollama_url,
        embedding_model=args.embedding_model,
        store_dir=store_dir,
    )


if __name__ == "__main__":
    main()
