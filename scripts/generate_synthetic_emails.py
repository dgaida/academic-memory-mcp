"""Skript zur Generierung künstlicher E-Mails basierend auf Klassenprofilen."""

import os
import sqlite3
import numpy as np
import pickle
import logging
from pathlib import Path
from mcp_university.config import get_config
from mcp_university.utils.llm_client_wrapper import LLMClientWrapper
from mcp_university.parser.mail_parser import MailParser

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_closest_to_centroid(embeddings: np.ndarray, n: int = 5) -> np.ndarray:
    """Findet die n Vektoren, die am nächsten am Zentroiden liegen.

    Args:
        embeddings (np.ndarray): Matrix der Embeddings.
        n (int): Anzahl der auszuwählenden Beispiele.

    Returns:
        np.ndarray: Indizes der repräsentativsten Vektoren.
    """
    centroid = np.mean(embeddings, axis=0)
    distances = np.linalg.norm(embeddings - centroid, axis=1)
    closest_indices = np.argsort(distances)[:n]
    return closest_indices

def create_msg_file(path: Path, subject: str, body: str) -> None:
    """Erstellt eine künstliche .msg Datei (Text-Fallback).

    Args:
        path (Path): Zielpfad.
        subject (str): Betreff.
        body (str): Inhalt.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Subject: {subject}\n\n{body}")

def main() -> None:
    """Generiert synthetische E-Mails für unterrepräsentierte Klassen."""
    config = get_config()
    llm = LLMClientWrapper()
    parser = MailParser()

    db_path = config.data_dir / "metadata" / "email_embeddings.db"
    train_path = Path("data/classifier/train")

    if not db_path.exists():
        logger.error(f"Embedding-Datenbank {db_path} nicht gefunden.")
        return

    conn = sqlite3.connect(db_path)

    for class_dir in train_path.iterdir():
        if not class_dir.is_dir():
            continue

        summary_path = class_dir / "augmentation_summary.md"
        if not summary_path.exists():
            continue

        class_name = class_dir.name
        logger.info(f"Generiere künstliche E-Mails für Klasse: {class_name}")

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = f.read()

        cursor = conn.cursor()
        cursor.execute("SELECT path, embedding FROM email_embeddings WHERE label = ?", (class_name,))
        rows = cursor.fetchall()

        if not rows:
            continue

        paths = [r[0] for r in rows]
        embeddings = np.array([pickle.loads(r[1]) for r in rows])

        n_examples = min(5, len(paths))
        closest_idx = get_closest_to_centroid(embeddings, n=n_examples)

        examples = []
        for idx in closest_idx:
            path = Path(paths[idx])
            text = parser.parse(path)
            if not text:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    text = "Beispielinhalt"
            examples.append(text)

        examples_str = "\n---\n".join(examples)

        prompt = f"""
Du bist ein System zur Datengenerierung. Erstelle 3 neue, künstliche E-Mails für '{class_name}'.
Zusammenfassung:
{summary}
Beispiele:
{examples_str}
Gib für jede E-Mail einen 'BETREFF:' und einen 'BODY:' an. Trenne die E-Mails durch '==='.
"""

        try:
            response = llm.chat([{"role": "user", "content": prompt}])
            synthetic_content = response.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"LLM Call fehlgeschlagen: {e}. Nutze Fallback-Generierung.")
            synthetic_content = "BETREFF: Künstliche Mail 1\nBODY: Dies ist ein künstlicher Text.\n===\nBETREFF: Künstliche Mail 2\nBODY: Ein weiterer künstlicher Text."

        emails = synthetic_content.split("===")
        for i, email_raw in enumerate(emails):
            if "BETREFF:" not in email_raw:
                continue

            try:
                parts = email_raw.split("BODY:", 1)
                subject = parts[0].replace("BETREFF:", "").strip()
                body = parts[1].strip()

                output_path = class_dir / "Inbox" / f"synthetic_{i}.msg"
                create_msg_file(output_path, subject, body)
                logger.info(f"  Gespeichert: {output_path}")
            except Exception as e:
                logger.error(f"Fehler beim Parsen der generierten Mail {i}: {e}")

    conn.close()

if __name__ == "__main__":
    main()
