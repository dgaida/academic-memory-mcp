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
    """Findet die signifikantesten Wörter pro Klasse.

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

    # TF-IDF Vectorizer mit deutschen Stoppwörtern
    # Da sklearn standardmäßig keine deutschen Stoppwörter hat,
    # verwenden wir eine einfache Liste oder vertrauen darauf, dass
    # die signifikantesten Wörter klassenspezifisch genug sind.
    # Wir nutzen 'german' falls verfügbar, ansonsten laden wir Texte.
    vectorizer = TfidfVectorizer(max_features=5000, stop_words=None) # standardmäßig

    X = vectorizer.fit_transform(texts)
    feature_names = np.array(vectorizer.get_feature_names_out())

    unique_labels = sorted(list(set(labels)))
    results = {}

    for label in unique_labels:
        # Indizes der Dokumente dieser Klasse
        indices = [i for i, lbl in enumerate(labels) if lbl == label]

        # TF-IDF Matrix für diese Klasse
        class_tfidf = X[indices]

        # Durchschnittlicher TF-IDF Wert pro Wort in dieser Klasse
        mean_tfidf = np.asarray(class_tfidf.mean(axis=0)).flatten()

        # Top N Indizes
        top_indices = mean_tfidf.argsort()[::-1][:top_n]

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
        print(f"Top {args.top_n} Wörter pro Klasse (TF-IDF Basis)")
        print("="*40)
        for class_name, top_words in results.items():
            print(f"\nKlasse: {class_name}")
            print(f"Top Wörter: {', '.join(top_words)}")
        print("="*40)

if __name__ == "__main__":
    main()
