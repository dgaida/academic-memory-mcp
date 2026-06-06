"""Skript zur Klassifizierung von E-Mails in einem Ordner und Verschieben in Klassen-Unterordner."""
import argparse
import logging
import shutil
from pathlib import Path
from typing import Optional

from mcp_university.classifier.engine import EmailClassifier, resolve_model_path

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def classify_and_move(source_dir: Path, model_path: Path, output_dir: Optional[Path] = None) -> None:
    """Klassifiziert E-Mails in einem Ordner und verschiebt sie in Unterordner basierend auf der Klasse.

    Args:
        source_dir: Quellordner mit .msg Dateien.
        model_path: Pfad zum trainierten Modell.
        output_dir: Zielordner. Wenn None, wird der Quellordner verwendet.
    """
    if output_dir is None:
        output_dir = source_dir

    classifier = EmailClassifier()
    classifier.load(model_path)

    # Alle .msg Dateien im Quellordner (nicht rekursiv laut Anforderung "einen Ordner")
    # Falls rekursiv gewünscht, .rglob nutzen. Anforderung sagt "einen Ordner".
    msg_files = list(source_dir.glob("*.msg"))

    if not msg_files:
        logger.info(f"Keine .msg Dateien in {source_dir} gefunden.")
        return

    logger.info(f"Gefunden: {len(msg_files)} Dateien in {source_dir}")

    for msg_file in msg_files:
        try:
            prediction = classifier.predict(msg_file)
            label = prediction["prediction"]

            target_dir = output_dir / label
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / msg_file.name

            # Falls Datei am Zielort bereits existiert, Namen anpassen
            if target_path.exists():
                counter = 1
                while True:
                    new_name = f"{msg_file.stem}_{counter}{msg_file.suffix}"
                    target_path = target_dir / new_name
                    if not target_path.exists():
                        break
                    counter += 1

            shutil.move(str(msg_file), str(target_path))
            logger.info(f"Verschoben: {msg_file.name} -> {target_path}")

        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von {msg_file.name}: {e}")


def main() -> None:
    """Haupteinstiegspunkt für das Skript."""
    parser = argparse.ArgumentParser(description="Klassifiziert E-Mails in einem Ordner und verschiebt sie in Klassen-Unterordner.")
    parser.add_argument("source_dir", type=str, help="Quellordner mit .msg Dateien.")
    parser.add_argument("--model", type=str, default="data/email_classifier.pkl", help="Pfad zum trainierten Modell.")
    parser.add_argument("--output-dir", type=str, help="Zielordner (standardmäßig Quellordner).")
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="tfidf",
                        help="Modus der Merkmalsextraktion (default: tfidf).")
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="transformer",
                        help="Klassifizierungsmethode (default: transformer).")

    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    model_path = resolve_model_path(args.model, args.method, args.mode)
    output_dir = Path(args.output_dir) if args.output_dir else None

    if not source_dir.exists():
        logger.error(f"Quellverzeichnis {source_dir} existiert nicht.")
        return

    if not model_path.exists():
        logger.error(f"Modell {model_path} existiert nicht.")
        return

    classify_and_move(source_dir, model_path, output_dir)


if __name__ == "__main__":
    main()
