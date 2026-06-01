"""Skript zum Finden der signifikantesten Wörter pro Klasse mittels TF-IDF."""
import argparse
import logging
from pathlib import Path
from typing import List, Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from mcp_university.classifier.engine import EmailClassifier

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_top_words_per_class(data_dir: Path, top_n: int = 5) -> Dict[str, List[str]]:
    """Findet die signifikantesten Wörter pro Klasse mittels klassenbasiertem TF-IDF.

    Hierbei werden alle E-Mails einer Klasse zu einem großen Dokument zusammengefasst,
    um die Einzigartigkeit von Wörtern für eine Klasse im Vergleich zu anderen Klassen
    zu bestimmen.

    Args:
        data_dir: Pfad zum Verzeichnis mit den Daten (Unterordner pro Klasse).
        top_n: Anzahl der Wörter pro Klasse.

    Returns:
        Dictionary mit Klassennamen als Keys und Listen von Top-Wörtern als Values.
    """
    classifier = EmailClassifier()
    logger.info(f"Lade Daten aus {data_dir}...")
    texts, labels = classifier.preprocess_data(data_dir)

    if not texts:
        logger.error(f"Keine Daten in {data_dir} gefunden.")
        return {}

    # Gruppiere Texte nach Klassen und konkateniere sie
    class_documents = {}
    for text, label in zip(texts, labels):
        if label not in class_documents:
            class_documents[label] = []
        class_documents[label].append(text)

    unique_labels = sorted(class_documents.keys())
    # Konkateniere alle Texte einer Klasse zu einem einzigen Dokument
    concatenated_docs = [" ".join(class_documents[label]) for label in unique_labels]

    # TF-IDF Vectorizer
    # Wir nutzen standardmäßig keine festen Stoppwörter, da klassenspezifische Begriffe
    # durch IDF ohnehin höher gewichtet werden als allgemeine Begriffe.
    vectorizer = TfidfVectorizer(max_features=5000)

    # Berechne TF-IDF auf den klassenbasierten Dokumenten
    X = vectorizer.fit_transform(concatenated_docs)
    feature_names = np.array(vectorizer.get_feature_names_out())

    results = {}

    for i, label in enumerate(unique_labels):
        # TF-IDF Werte für diese Klasse (Zeile i in der Matrix)
        class_tfidf = X[i].toarray().flatten()

        # Top N Indizes
        top_indices = class_tfidf.argsort()[::-1][:top_n]

        results[label] = feature_names[top_indices].tolist()

    return results

def main():
    """Main Entry Point."""
    parser = argparse.ArgumentParser(description="Findet die signifikantesten Wörter pro E-Mail-Klasse.")
    parser.add_argument("data_dir", type=str, help="Pfad zum Verzeichnis mit den Daten.")
    parser.add_argument("--top-n", type=int, default=5, help="Anzahl der Wörter pro Klasse (default: 5).")

    args = parser.parse_args()
    data_path = Path(args.data_dir)

    if not data_path.exists():
        logger.error(f"Pfad {data_path} existiert nicht.")
        return

    results = get_top_words_per_class(data_path, args.top_n)

    if results:
        print("\n" + "="*40)
        print(f"Top {args.top_n} Wörter pro Klasse (Klassenbasiertes TF-IDF)")
        print("="*40)
        for class_name, top_words in results.items():
            print(f"\nKlasse: {class_name}")
            print(f"Top Wörter: {', '.join(top_words)}")
        print("="*40)

if __name__ == "__main__":
    main()
