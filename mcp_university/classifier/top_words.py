"""Skript zum Finden der signifikantesten Wörter pro Klasse mittels TF-IDF."""
import argparse
import logging
from mcp_university.classifier.stopwords import ALL_STOP_WORDS
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

from mcp_university.classifier.engine import EmailClassifier

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_detailed_stats(data_dir: Path, top_n: int = 5) -> Dict[str, Any]:
    """Berechnet detaillierte TF-IDF Statistiken pro Klasse und global.

    Args:
        data_dir: Pfad zum Verzeichnis mit den Daten.
        top_n: Anzahl der Wörter pro Kategorie.

    Returns:
        Dictionary mit globalen und klassenspezifischen Statistiken.
    """
    classifier = EmailClassifier()
    logger.info(f"Lade Daten aus {data_dir}...")
    texts, labels = classifier.preprocess_data(data_dir)

    if not texts:
        logger.error(f"Keine Daten in {data_dir} gefunden.")
        return {}

    # 1. Globale Term-Frequenz (TF)
    cv_global = CountVectorizer(max_features=5000, stop_words=ALL_STOP_WORDS)
    global_tf_matrix = cv_global.fit_transform(texts)
    global_tf_sums = np.array(global_tf_matrix.sum(axis=0)).flatten()
    global_feature_names = np.array(cv_global.get_feature_names_out())

    global_top_tf_indices = global_tf_sums.argsort()[::-1][:top_n]
    global_top_tf = [
        {"word": global_feature_names[i], "count": int(global_tf_sums[i])}
        for i in global_top_tf_indices
    ]

    # 2. Klassenbasierte Analyse
    class_documents = {}
    for text, label in zip(texts, labels):
        if label not in class_documents:
            class_documents[label] = []
        class_documents[label].append(text)

    unique_labels = sorted(class_documents.keys())
    concatenated_docs = [" ".join(class_documents[label]) for label in unique_labels]

    # TF-IDF auf Klassenebene
    tfidf_vec = TfidfVectorizer(max_features=5000, stop_words=ALL_STOP_WORDS, sublinear_tf=True, token_pattern=r"(?u)\b[a-zA-ZäöüÄÖÜß]{2,}\b")
    tfidf_matrix = tfidf_vec.fit_transform(concatenated_docs)
    tfidf_feature_names = np.array(tfidf_vec.get_feature_names_out())
    idf_values = tfidf_vec.idf_

    # CountVectorizer auf Klassenebene für TF pro Klasse
    cv_class = CountVectorizer(vocabulary=tfidf_vec.vocabulary_, stop_words=ALL_STOP_WORDS)
    class_tf_matrix = cv_class.fit_transform(concatenated_docs)

    class_stats = {}
    for i, label in enumerate(unique_labels):
        # TF-IDF
        class_tfidf = tfidf_matrix[i].toarray().flatten()
        top_tfidf_idx = class_tfidf.argsort()[::-1][:top_n]

        # TF (Häufigkeit in dieser Klasse)
        class_tf = class_tf_matrix[i].toarray().flatten()
        top_tf_idx = class_tf.argsort()[::-1][:top_n]

        # IDF (Höchste IDF-Werte für Wörter, die in dieser Klasse vorkommen)
        # Wir filtern nach Wörtern die in der Klasse vorkommen (TF > 0)
        present_mask = class_tf > 0
        class_idf_values = idf_values.copy()
        class_idf_values[~present_mask] = -1 # Ignoriere Wörter die nicht vorkommen
        top_idf_idx = class_idf_values.argsort()[::-1][:top_n]

        class_stats[label] = {
            "top_tfidf": tfidf_feature_names[top_tfidf_idx].tolist(),
            "top_tf": [
                {"word": tfidf_feature_names[idx], "count": int(class_tf[idx])}
                for idx in top_tf_idx
            ],
            "top_idf": [
                {"word": tfidf_feature_names[idx], "idf": float(idf_values[idx])}
                for idx in top_idf_idx if class_idf_values[idx] != -1
            ]
        }

    return {
        "global_top_tf": global_top_tf,
        "class_stats": class_stats
    }

def get_top_words_per_class(data_dir: Path, top_n: int = 5) -> Dict[str, List[str]]:
    """Legacy-Wrapper für Abwärtskompatibilität mit Tests."""
    stats = get_detailed_stats(data_dir, top_n)
    if not stats:
        return {}
    return {label: data["top_tfidf"] for label, data in stats["class_stats"].items()}

def main():
    """Main Entry Point."""
    parser = argparse.ArgumentParser(description="Findet die signifikantesten Wörter pro E-Mail-Klasse.")
    parser.add_argument("data_dir", type=str, help="Pfad zum Verzeichnis mit den Daten.")
    parser.add_argument("--top-n", type=int, default=5, help="Anzahl der Wörter pro Kategorie (default: 5).")

    args = parser.parse_args()
    data_path = Path(args.data_dir)

    if not data_path.exists():
        logger.error(f"Pfad {data_path} existiert nicht.")
        return

    stats = get_detailed_stats(data_path, args.top_n)

    if stats:
        print("\n" + "="*60)
        print(f"GLOBALE ANALYSE (Top {args.top_n} am häufigsten im gesamten Datensatz)")
        print("-"*60)
        for item in stats["global_top_tf"]:
            print(f"{item['word']:20} | Count: {item['count']}")

        print("\n" + "="*60)
        print(f"KLASSENSPEZIFISCHE ANALYSE (Top {args.top_n})")
        print("="*60)

        for class_name, data in stats["class_stats"].items():
            print(f"\nKLASSE: {class_name}")
            print("-" * 30)

            print(f"{'TF-IDF (Signifikanz)':25}: {', '.join(data['top_tfidf'])}")

            tf_str = ", ".join([f"{item['word']} ({item['count']})" for item in data['top_tf']])
            print(f"{'TF (Häufigkeit)':25}: {tf_str}")

            idf_str = ", ".join([f"{item['word']} ({item['idf']:.2f})" for item in data['top_idf']])
            print(f"{'IDF (Seltenheit)':25}: {idf_str}")
            print("-" * 60)

if __name__ == "__main__":
    main()
