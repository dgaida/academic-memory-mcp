"""Skript zur 2D-Visualisierung von E-Mail-Embeddings mittels t-SNE."""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.manifold import TSNE
import logging
import pickle

from mcp_university.config import get_config
from mcp_university.retrieval.index import get_model
from mcp_university.parser.mail_parser import MailParser

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialisiert die SQLite Datenbank für Embeddings.

    Args:
        db_path (Path): Pfad zur Datenbankdatei.

    Returns:
        sqlite3.Connection: Verbindung zur Datenbank.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_embeddings (
            path TEXT PRIMARY KEY,
            label TEXT,
            embedding BLOB
        )
    ''')
    conn.commit()
    return conn

def get_cached_embedding(conn: sqlite3.Connection, path: Path) -> np.ndarray:
    """Holt ein Embedding aus dem Cache.

    Args:
        conn (sqlite3.Connection): DB-Verbindung.
        path (Path): Pfad zur Datei.

    Returns:
        np.ndarray: Das geladene Embedding oder None.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT embedding FROM email_embeddings WHERE path = ?", (str(path),))
    row = cursor.fetchone()
    if row:
        return pickle.loads(row[0])
    return None

def save_embedding(conn: sqlite3.Connection, path: Path, label: str, embedding: np.ndarray) -> None:
    """Speichert ein Embedding im Cache.

    Args:
        conn (sqlite3.Connection): DB-Verbindung.
        path (Path): Pfad zur Datei.
        label (str): Klassenname.
        embedding (np.ndarray): Der Vektor.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO email_embeddings (path, label, embedding) VALUES (?, ?, ?)",
        (str(path), label, pickle.dumps(embedding))
    )
    conn.commit()

def main() -> None:
    """Hauptfunktion zur Berechnung und Visualisierung der Embeddings."""
    config = get_config()
    db_path = config.data_dir / "metadata" / "email_embeddings.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = init_db(db_path)

    train_path = Path("data/classifier/train")

    if not train_path.exists():
        logger.error(f"Trainingspfad {train_path} existiert nicht.")
        return

    logger.info(f"Lade Modell: {config.embeddings.model}")
    model = get_model(config.embeddings.model, offline=config.offline)
    parser = MailParser()

    data = []

    msg_files = list(train_path.rglob("*.msg"))
    logger.info(f"Gefundene .msg Dateien: {len(msg_files)}")

    for file_path in msg_files:
        # data/classifier/train/CLASS/Folder/file.msg
        label = file_path.parent.parent.name

        embedding = get_cached_embedding(conn, file_path)

        if embedding is None:
            logger.info(f"Berechne Embedding für {file_path}")
            text = parser.parse(file_path)
            if not text:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            embedding = model.encode(text)
            save_embedding(conn, file_path, label, embedding)

        data.append({
            "path": str(file_path),
            "label": label,
            "embedding": embedding
        })

    if not data:
        logger.warning("Keine Daten für die Projektion gefunden.")
        return

    logger.info("Starte t-SNE Projektion...")
    embeddings_matrix = np.array([d["embedding"] for d in data])
    labels = [d["label"] for d in data]

    perp = min(30, len(data) - 1)
    tsne = TSNE(n_components=2, perplexity=perp, random_state=42, init='pca', learning_rate='auto')
    projections = tsne.fit_transform(embeddings_matrix)

    df = pd.DataFrame(projections, columns=["x", "y"])
    df["Klasse"] = labels

    logger.info("Erstelle Plot...")
    plt.figure(figsize=(12, 8))
    sns.scatterplot(data=df, x="x", y="y", hue="Klasse", palette="viridis", s=100, alpha=0.7)
    plt.title("t-SNE Projektion der E-Mail Embeddings")
    plt.grid(True, linestyle='--', alpha=0.6)

    plot_path = config.data_dir / "plots" / "embeddings_tsne.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(plot_path)
    logger.info(f"Plot gespeichert unter: {plot_path}")

    conn.close()

if __name__ == "__main__":
    main()
