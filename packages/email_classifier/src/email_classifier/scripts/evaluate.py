"""Skript zur Evaluierung des E-Mail-Klassifikators."""
import argparse
from pathlib import Path
import logging

from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

from email_classifier.engine import EmailClassifier, resolve_model_path
from mcp_university.utils.torch_utils import get_device

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

    # Vorhersagen
    if classifier.method == 'transformer':
        device = get_device()
        classifier.classifier.to(device)
        classifier.classifier.eval()
        y_pred_idx = []
        with torch.no_grad():
            # Batchweise Verarbeitung für Evaluierung
            logger.info(f'Tokenisiere {len(texts)} Texte für die Evaluierung...')
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors='pt')
            dataset = TensorDataset(encodings['input_ids'], encodings['attention_mask'])
            loader = DataLoader(dataset, batch_size=8)
            num_batches = len(loader)
            logger.info(f'Starte Batch-Vorhersage ({num_batches} Batches)...')
            for i, batch in enumerate(loader):
                ids, mask = [t.to(device) for t in batch]
                outputs = classifier.classifier(ids, mask)
                preds = torch.argmax(outputs, dim=1)
                y_pred_idx.extend(preds.cpu().numpy())
                if (i + 1) % 10 == 0 or (i + 1) == num_batches:
                    logger.info(f'Evaluierung: Batch {i + 1}/{num_batches} verarbeitet.')
        y_pred_idx = np.array(y_pred_idx)
    else:
        # Merkmale extrahieren für klassische Modelle
        X = classifier.get_features(texts, train=False)
        y_pred_idx = classifier.classifier.predict(X)
    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx.astype(int))

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
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="combined",
                        help="Modus der Merkmalsextraktion (default: combined).")
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="transformer",
                        help="Klassifizierungsmethode (default: transformer).")

    args = parser.parse_args()

    model_path = resolve_model_path(args.model_path, args.method, args.mode)

    evaluate(model_path, Path(args.test_dir))

if __name__ == "__main__":
    main()
