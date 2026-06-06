"""Skript zur Vorhersage mit dem E-Mail-Klassifikator."""
import argparse
import json
from pathlib import Path
import logging

from mcp_university.classifier.engine import EmailClassifier, resolve_model_path

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main() -> None:
    """Main function for classifying an email."""
    parser = argparse.ArgumentParser(description="Klassifiziert eine E-Mail Datei.")
    parser.add_argument("file_path", type=str, help="Pfad zur .msg oder .eml Datei.")
    parser.add_argument("--model-path", type=str, default="data/email_classifier.pkl", help="Pfad zum trainierten Modell.")
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="tfidf",
                        help="Modus der Merkmalsextraktion (default: tfidf).")
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="transformer",
                        help="Klassifizierungsmethode (default: transformer).")
    parser.add_argument("--json", action="store_true", help="Ausgabe im JSON-Format.")

    args = parser.parse_args()

    model_path = resolve_model_path(args.model_path, args.method, args.mode)
    if not model_path.exists():
        logger.error(f"Modell {model_path} wurde nicht gefunden. Bitte zuerst trainieren.")
        return

    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"Datei {args.file_path} existiert nicht.")
        return

    classifier = EmailClassifier()
    try:
        classifier.load(model_path)
        result = classifier.predict(file_path)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\nVorhersage für: {file_path.name}")
            print(f"Klasse: {result['prediction']}")
            print(f"Konfidenz: {result['confidence']:.2%}")
            print("\nWahrscheinlichkeiten:")
            for label, prob in sorted(result['probabilities'].items(), key=lambda x: x[1], reverse=True):
                if prob > 0.01:
                    print(f"  - {label}: {prob:.2%}")

    except Exception as e:
        logger.error(f"Fehler bei der Klassifizierung: {e}")


if __name__ == "__main__":
    main()
