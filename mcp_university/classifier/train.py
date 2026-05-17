"""Skript zum Trainieren des E-Mail-Klassifikators."""
import argparse
from pathlib import Path
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from mcp_university.classifier.engine import EmailClassifier

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def evaluate_and_save(classifier: EmailClassifier, texts: list, labels: list, output_dir: Path, prefix: str = "train") -> None:
    """Evaluiert das Modell und speichert Metriken und Konfusionsmatrix.

    Args:
        classifier: Der trainierte Klassifikator.
        texts: Liste der Texte.
        labels: Liste der wahren Labels.
        output_dir: Verzeichnis zum Speichern der Ergebnisse.
        prefix: Präfix für die Dateinamen.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Vorhersagen
    X = classifier._get_features(texts, train=False)
    y_pred_idx = classifier.classifier.predict(X)
    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx)

    # Metriken berechnen
    accuracy = accuracy_score(labels, y_pred)
    report = classification_report(labels, y_pred)
    cm = confusion_matrix(labels, y_pred, labels=classifier.label_encoder.classes_)

    # 1. Konfusionsmatrix plotten
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=classifier.label_encoder.classes_,
                yticklabels=classifier.label_encoder.classes_)
    plt.title(f'Konfusionsmatrix ({prefix.capitalize()})')
    plt.ylabel('Wahre Klasse')
    plt.xlabel('Vorhergesagte Klasse')
    plt.tight_layout()

    img_path = output_dir / f"{prefix}_confusion_matrix.png"
    plt.savefig(img_path, dpi=300)
    plt.close()
    logger.info(f"Konfusionsmatrix gespeichert unter {img_path}")

    # 2. Metriken in MD-Datei speichern
    md_path = output_dir / f"{prefix}_metrics.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Evaluierungsergebnisse ({prefix})\n\n")
        f.write(f"**Genauigkeit (Accuracy):** {accuracy:.2%}\n\n")
        f.write("## Klassifizierungsbericht\n\n")
        f.write("```\n")
        f.write(report)
        f.write("\n```\n\n")
        f.write("## Konfusionsmatrix\n\n")
        cm_df = pd.DataFrame(cm, index=classifier.label_encoder.classes_, columns=classifier.label_encoder.classes_)
        f.write(cm_df.to_markdown())
        f.write("\n")

    logger.info(f"Metriken gespeichert unter {md_path}")

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
        # Daten laden für spätere Evaluierung
        texts, labels = classifier.preprocess_data(data_path)

        # Training
        classifier.train(data_path)

        # Sicherstellen, dass Zielverzeichnis existiert
        model_file = Path(args.model_path)
        model_file.parent.mkdir(parents=True, exist_ok=True)

        classifier.save(model_file)
        logger.info(f"Modell erfolgreich trainiert und unter {args.model_path} gespeichert.")

        # Evaluierung auf Trainingsdaten
        logger.info("Starte Evaluierung auf Trainingsdaten...")
        evaluate_and_save(classifier, texts, labels, model_file.parent, prefix="train")

    except Exception as e:
        logger.error(f"Fehler beim Training: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
