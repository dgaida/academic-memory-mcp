"""Skript zum Trainieren des E-Mail-Klassifikators."""
from mcp_university.classifier.engine import EmailClassifier
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV
from torch.utils.data import DataLoader, TensorDataset
import argparse
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def evaluate_and_save(classifier: EmailClassifier, texts: list, labels: list, output_dir: Path, prefix: str = "train", cv_results: dict = None) -> None:
    """Evaluiert das Modell und speichert Metriken und Konfusionsmatrix.

    Args:
        classifier: Der trainierte Klassifikator.
        texts: Liste der Texte.
        labels: Liste der wahren Labels.
        output_dir: Verzeichnis zum Speichern der Ergebnisse.
        prefix: Präfix für die Dateinamen.
        cv_results: Ergebnisse der Kreuzvalidierung (optional).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Vorhersagen
    if classifier.method == "transformer":
        classifier.classifier.eval()
        y_pred_idx = []
        with torch.no_grad():
            # Batchweise Verarbeitung für Evaluierung
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset = TensorDataset(encodings["input_ids"], encodings["attention_mask"])
            loader = DataLoader(dataset, batch_size=8)
            for batch in loader:
                ids, mask = batch
                outputs = classifier.classifier(ids, mask)
                preds = torch.argmax(outputs, dim=1)
                y_pred_idx.extend(preds.numpy())
        y_pred_idx = np.array(y_pred_idx)
    else:
        X = classifier.get_features(texts, train=False)
        y_pred_idx = classifier.classifier.predict(X)

    y_pred = classifier.label_encoder.inverse_transform(y_pred_idx.astype(int))

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

        if cv_results:
            f.write("## Kreuzvalidierung (Cross-Validation)\n\n")
            f.write(f"**Beste Parameter:** `{cv_results['best_params']}`\n\n")
            f.write(f"**Bester CV-Score (Accuracy):** {cv_results['best_score']:.2%}\n\n")
            f.write("### Alle Experimente\n\n")
            cv_df = pd.DataFrame(cv_results['results'])
            # Nur relevante Spalten anzeigen
            cols = [col for col in cv_df.columns if col.startswith('param_') or col in ['mean_test_score', 'std_test_score', 'rank_test_score']]
            f.write(cv_df[cols].sort_values('rank_test_score').to_markdown(index=False))
            f.write("\n\n")

        f.write(f"**Genauigkeit auf Trainingsdaten (Accuracy):** {accuracy:.2%}\n\n")
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
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="xgboost",
                        help="Klassifizierungsmethode (default: xgboost).")
    parser.add_argument("--embedding-model", type=str, default="paraphrase-multilingual-MiniLM-L12-v2",
                        help="Sentence-Transformer Modell (default: paraphrase-multilingual-MiniLM-L12-v2).")

    args = parser.parse_args()

    data_path = Path(args.data_dir)
    if not data_path.exists():
        logger.error(f"Datenverzeichnis {args.data_dir} existiert nicht.")
        return

    logger.info(f"Starte Training im Modus '{args.mode}' mit Methode '{args.method}'...")
    classifier = EmailClassifier(mode=args.mode, method=args.method, embedding_model_name=args.embedding_model)

    try:
        # Daten laden
        texts, labels = classifier.preprocess_data(data_path)
        if not texts:
            logger.error(f"Keine Trainingsdaten in {args.data_dir} gefunden.")
            return

        # Labels encoden
        y = classifier.label_encoder.fit_transform(labels)
        num_classes = len(classifier.label_encoder.classes_)

        if args.method == "transformer":
            logger.info("Starte Transformer Fine-Tuning...")
            from mcp_university.classifier.engine import EmailTransformerClassifier
            classifier.classifier = EmailTransformerClassifier(args.embedding_model, num_classes)

            # Tokenisierung
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset = TensorDataset(encodings["input_ids"], encodings["attention_mask"], torch.tensor(y))
            loader = DataLoader(dataset, batch_size=8, shuffle=True)

            optimizer = torch.optim.AdamW(classifier.classifier.parameters(), lr=2e-5)
            criterion = torch.nn.CrossEntropyLoss()

            classifier.classifier.train()
            for epoch in range(3): # 3 Epochen als Standard
                total_loss = 0
                for batch in loader:
                    optimizer.zero_grad()
                    input_ids, mask, targets = batch
                    outputs = classifier.classifier(input_ids, mask)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                logger.info(f"Epoch {epoch+1}/3, Loss: {total_loss/len(loader):.4f}")

            classifier.is_trained = True
            cv_results = None # Keine CV für Transformer in diesem einfachen Loop
        else:
            # Merkmale extrahieren für klassische Modelle
            X = classifier.get_features(texts, train=True)

            # GridSearchCV Setup
            if args.method == "randomforest":
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20],
                    'criterion': ['gini']
                }
            else:  # xgboost
                param_grid = {
                    'n_estimators': [100, 200],
                    'max_depth': [2, 3],
                    'learning_rate': [0.1]
                }

            logger.info(f"Starte GridSearchCV mit 5-fold CV und 9 Experimenten für {args.method}...")
            grid_search = GridSearchCV(
                estimator=classifier.classifier,
                param_grid=param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1,
                verbose=1
            )

            grid_search.fit(X, y)

            logger.info(f"Beste Parameter: {grid_search.best_params_}")
            logger.info(f"Bester Score: {grid_search.best_score_:.4f}")

            # Bestes Modell in den Classifier übernehmen
            classifier.classifier = grid_search.best_estimator_
            classifier.is_trained = True

            if args.method != "transformer":
                # CV Ergebnisse für den Bericht vorbereiten
                cv_results = {
                    'best_params': grid_search.best_params_,
                    'best_score': grid_search.best_score_,
                    'results': grid_search.cv_results_
                }

        # Sicherstellen, dass Zielverzeichnis existiert
        model_file = Path(args.model_path)
        if f"_{args.mode}" not in model_file.stem:
            model_file = model_file.with_name(f"{model_file.stem}_{args.mode}{model_file.suffix}")
        model_file.parent.mkdir(parents=True, exist_ok=True)

        classifier.save(model_file)
        logger.info(f"Modell erfolgreich trainiert und unter {model_file} gespeichert.")

        # Evaluierung auf Trainingsdaten
        logger.info("Starte Evaluierung und Berichterstellung...")
        evaluate_and_save(classifier, texts, labels, model_file.parent, prefix="train", cv_results=cv_results)

    except Exception as e:
        logger.error(f"Fehler beim Training: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()