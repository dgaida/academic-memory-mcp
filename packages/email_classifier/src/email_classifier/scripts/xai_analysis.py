"""XAI Analyse für den E-Mail-Klassifikator."""
import argparse
from pathlib import Path
import logging
from collections import Counter
import numpy as np
import shap

from email_classifier.engine import EmailClassifier, resolve_model_path

from mcp_university.utils.anonymizer import anonymize_th_koeln_names
# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_xai_analysis(model_path: Path, test_data_path: Path, samples_per_class: int = 120, top_n_words: int = 15) -> None:
    """Führt eine XAI-Analyse mit SHAP durch.

    Args:
        model_path: Pfad zum Modell.
        test_data_path: Pfad zu den Testdaten.
        samples_per_class: Anzahl der Datenpunkte pro Klasse.
        top_n_words: Anzahl der wichtigsten Wörter pro Datenpunkt.
    """
    if not model_path.exists():
        logger.error(f"Modell {model_path} nicht gefunden.")
        return

    if not test_data_path.exists():
        logger.error(f"Testdaten-Verzeichnis {test_data_path} nicht gefunden.")
        return

    # Modell laden
    classifier = EmailClassifier()
    classifier.load(model_path)

    if classifier.mode != "tfidf":
        logger.error("XAI Analyse aktuell nur für TF-IDF Modelle unterstützt.")
        return

    # SHAP Explainer initialisieren
    explainer = shap.TreeExplainer(classifier.classifier)

    feature_names = classifier.tfidf_vectorizer.get_feature_names_out()
    classes = classifier.label_encoder.classes_

    results = {}

    for class_name in classes:
        logger.info(f"Analysiere Klasse: {class_name}")
        class_dir = test_data_path / class_name
        if not class_dir.exists():
            logger.warning(f"Verzeichnis für Klasse {class_name} nicht gefunden.")
            continue

        # Sammle bis zu samples_per_class E-Mails
        files = list(class_dir.rglob("*.msg"))[:samples_per_class]
        if not files:
            logger.warning(f"Keine .msg Dateien für Klasse {class_name} gefunden.")
            continue

        class_word_counter = Counter()

        texts = []
        for file_path in files:
            # Fallback for dummy files that are not valid OLE2
            try:
                text = classifier._extract_text(file_path)
            except Exception:
                text = None

            if not text:
                text = file_path.read_text()

            if text:
                # Anonymisierung vor der Merkmalsextraktion für XAI
                text = anonymize_th_koeln_names(text)
                texts.append(text)

        if not texts:
            continue

        # Merkmale extrahieren
        X = classifier.tfidf_vectorizer.transform(texts).toarray()

        # SHAP Werte berechnen
        shap_values = explainer.shap_values(X)

        # class_idx for the label
        class_idx = list(classes).index(class_name)

        # Determine which shap_values array to use
        # For RandomForest/XGBoost shap_values is (samples, features, classes) or list of (samples, features)
        if isinstance(shap_values, list):
            current_shap_values = shap_values[class_idx]
        elif len(shap_values.shape) == 3: # (samples, features, classes)
             current_shap_values = shap_values[:, :, class_idx]
        else:
             # Binary or single output
             current_shap_values = shap_values

        for i in range(len(texts)):
            sample_shap = current_shap_values[i]
            top_indices = np.argsort(sample_shap)[-top_n_words:]

            for idx in top_indices:
                if sample_shap[idx] > 0:
                    word = feature_names[idx]
                    class_word_counter[word] += 1

        results[class_name] = [word for word, count in class_word_counter.most_common(5)]

    # Ergebnis ausgeben
    print("\n" + "="*40)
    print("XAI ANALYSE ERGEBNISSE (Top 5 Wörter pro Klasse)")
    print("="*40)
    for class_name, top_words in results.items():
        print(f"\nKlasse: {class_name}")
        if top_words:
            print(f"Top Wörter: {', '.join(top_words)}")
        else:
            print("Keine signifikanten Wörter gefunden.")

    # Globale Feature Importance ausgeben
    if hasattr(classifier.classifier, "feature_importances_"):
        print("\n" + "="*40)
        print("GLOBALE FEATURE IMPORTANCE (Top 10)")
        print("="*40)
        importances = classifier.classifier.feature_importances_
        indices = np.argsort(importances)[::-1][:10]

        for i in indices:
            print(f"{feature_names[i]:20} | Score: {importances[i]:.4f}")

    print("="*40)

def main() -> None:
    """Main Entry Point."""
    parser = argparse.ArgumentParser(description="XAI Analyse für E-Mail Klassifizierung.")
    parser.add_argument("--model-path", type=str, default="data/email_classifier.pkl", help="Pfad zum Modell.")
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="tfidf",
                        help="Modus der Merkmalsextraktion (default: tfidf).")
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="xgboost",
                        help="Klassifizierungsmethode (default: xgboost).")
    parser.add_argument("--test-data-path", type=str, default="test_mail_data", help="Pfad zu den Testdaten.")

    args = parser.parse_args()

    run_xai_analysis(resolve_model_path(args.model_path, args.method, args.mode), Path(args.test_data_path))

if __name__ == "__main__":
    main()
