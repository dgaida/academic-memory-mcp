"""Skript zum Trainieren des E-Mail-Klassifikators."""
import argparse
from pathlib import Path
import logging

from mcp_university.classifier.engine import EmailClassifier

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Main function for training the classifier."""
    parser = argparse.ArgumentParser(description="Trainiert einen E-Mail-Klassifikator.")
    parser.add_argument("data_dir", type=str, help="Pfad zum Verzeichnis mit den Trainingsdaten (Unterordner pro Klasse).")
    parser.add_argument("--model-path", type=str, default="data/email_classifier.pkl", help="Pfad zum Speichern des Modells.")
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="combined",
                        help="Modus der Merkmalsextraktion (default: combined).")
    parser.add_argument("--embedding-model", type=str, default="paraphrase-multilingual-MiniLM-L12-v2",
                        help="Sentence-Transformer Modell (default: paraphrase-multilingual-MiniLM-L12-v2).")

    args = parser.parse_args()

    data_path = Path(args.data_dir)
    if not data_path.exists():
        logger.error(f"Datenverzeichnis {args.data_dir} existiert nicht.")
        return

    logger.info(f"Starte Training im Modus '{args.mode}'...")
    classifier = EmailClassifier(mode=args.mode, embedding_model_name=args.embedding_model)

    try:
        classifier.train(data_path)

        # Sicherstellen, dass Zielverzeichnis existiert
        model_file = Path(args.model_path)
        model_file.parent.mkdir(parents=True, exist_ok=True)

        classifier.save(model_file)
        logger.info(f"Modell erfolgreich trainiert und unter {args.model_path} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Training: {e}")

if __name__ == "__main__":
    main()
