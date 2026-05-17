"""Skript zur Evaluierung des E-Mail-Klassifikators."""
import argparse
from pathlib import Path
import logging

from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from mcp_university.classifier.engine import EmailClassifier

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def evaluate(model_path: Path, test_dir: Path) -> None:
    """Evaluiert das Modell auf Testdaten.

    Args:
        model_path: Pfad zum trainierten Modell.
        test_dir: Verzeichnis mit Testdaten (Unterordner pro Klasse).
    """
    if not model_path.exists():
        logger.error(f"Modell {model_path} wurde nicht gefunden.")
        return

    if not test_dir.exists():
        logger.error(f"Testverzeichnis {test_dir} existiert nicht.")
        return

    classifier = EmailClassifier()
    classifier.load(model_path)

    logger.info(f"Lade Testdaten aus {test_dir}...")
    texts, y_true = classifier.preprocess_data(test_dir)

    if not texts:
        logger.error("Keine Testdaten gefunden.")
        return

    logger.info(f"{len(texts)} Test-E-Mails geladen. Starte Vorhersage...")

    # Merkmale extrahieren
    X = classifier._get_features(texts, train=False)

    # Vorhersagen
    y_pred_idx = classifier.classifier.predict(X)
    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx)

    # Metriken berechnen
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=classifier.label_encoder.classes_)

    # Ergebnisse ausgeben
    print("\n" + "="*30)
    print("EVALUIERUNGSERGEBNISSE")
    print("="*30)
    print(f"Genauigkeit (Accuracy): {accuracy:.2%}")
    print("\nKlassifizierungsbericht:")
    print(report)

    print("\nKonfusionsmatrix:")
    cm_df = pd.DataFrame(cm, index=classifier.label_encoder.classes_, columns=classifier.label_encoder.classes_)
    print(cm_df)
    print("="*30 + "\n")

    # 1. Konfusionsmatrix plotten und speichern
    output_dir = model_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
                xticklabels=classifier.label_encoder.classes_,
                yticklabels=classifier.label_encoder.classes_)
    plt.title('Konfusionsmatrix (Testdaten)')
    plt.ylabel('Wahre Klasse')
    plt.xlabel('Vorhergesagte Klasse')
    plt.tight_layout()

    img_path = output_dir / "test_confusion_matrix.png"
    plt.savefig(img_path, dpi=300)
    plt.close()
    logger.info(f"Konfusionsmatrix gespeichert unter {img_path}")

    # 2. Metriken in MD-Datei speichern
    md_path = output_dir / "test_metrics.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Evaluierungsergebnisse (Testdaten)\n\n")
        f.write(f"**Genauigkeit (Accuracy):** {accuracy:.2%}\n\n")
        f.write("## Klassifizierungsbericht\n\n")
        f.write("```\n")
        f.write(report)
        f.write("\n```\n\n")
        f.write("## Konfusionsmatrix\n\n")
        f.write(cm_df.to_markdown())
        f.write("\n")

    logger.info(f"Metriken gespeichert unter {md_path}")

def main() -> None:
    """Main function for evaluating the classifier."""
    parser = argparse.ArgumentParser(description="Evaluiert einen E-Mail-Klassifikator.")
    parser.add_argument("test_dir", type=str, help="Pfad zum Verzeichnis mit den Testdaten (Unterordner pro Klasse).")
    parser.add_argument("--model-path", type=str, default="data/email_classifier.pkl", help="Pfad zum trainierten Modell.")

    args = parser.parse_args()

    evaluate(Path(args.model_path), Path(args.test_dir))

if __name__ == "__main__":
    main()
