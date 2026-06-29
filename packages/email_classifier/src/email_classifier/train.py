"""Skript zum Trainieren des E-Mail-Klassifikators."""
from email_classifier.engine import EmailClassifier, resolve_model_path
from mcp_university.utils.torch_utils import get_device
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split
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
        device = get_device()
        classifier.classifier.to(device)
        with torch.no_grad():
            # Batchweise Verarbeitung für Evaluierung
            logger.info(f"Tokenisiere {len(texts)} Texte für die Evaluierung...")
            encodings = classifier.tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset = TensorDataset(encodings["input_ids"], encodings["attention_mask"])
            loader = DataLoader(dataset, batch_size=8)
            num_batches = len(loader)
            logger.info(f"Starte Batch-Vorhersage ({num_batches} Batches)...")
            for i, batch in enumerate(loader):
                ids, mask = [t.to(device) for t in batch]
                outputs = classifier.classifier(ids, mask)
                preds = torch.argmax(outputs, dim=1)
                y_pred_idx.extend(preds.cpu().numpy())
                if (i + 1) % 10 == 0 or (i + 1) == num_batches:
                    logger.info(f"Evaluierung: Batch {i + 1}/{num_batches} verarbeitet.")
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
    from mcp_university.config import get_config
    get_config() # Sicherstellen, dass .env geladen ist
    parser = argparse.ArgumentParser(description="Trainiert einen E-Mail-Klassifikator.")
    parser.add_argument("data_dir", type=str, help="Pfad zum Verzeichnis mit den Trainingsdaten (Unterordner pro Klasse).")
    parser.add_argument("--model-path", type=str, default="data/email_classifier.pkl", help="Pfad zum Speichern des Modells.")
    parser.add_argument("--mode", type=str, choices=["tfidf", "embedding", "combined"], default="tfidf",
                        help="Modus der Merkmalsextraktion (default: tfidf).")
    parser.add_argument("--method", type=str, choices=["randomforest", "xgboost", "transformer"], default="transformer",
                        help="Klassifizierungsmethode (default: transformer).")
    parser.add_argument("--embedding-model", type=str, default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        help="Sentence-Transformer Modell (default: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).")

    args = parser.parse_args()

    data_path = Path(args.data_dir)
    if not data_path.exists():
        logger.error(f"Datenverzeichnis {args.data_dir} existiert nicht.")
        return

    logger.info(f"Starte Training im Modus '{args.mode}' mit Methode '{args.method}'...")
    classifier = EmailClassifier(mode=args.mode, method=args.method, embedding_model_name=args.embedding_model)

    # Bestehendes Modell laden falls vorhanden
    model_file = resolve_model_path(args.model_path, args.method, args.mode)
    if model_file.exists():
        logger.info(f"Bestehendes Modell gefunden unter {model_file}. Lade für mögliches Weiter-Training...")
        try:
            classifier.load(model_file)
        except Exception as e:
            logger.warning(f"Bestehendes Modell konnte nicht geladen werden: {e}")

    try:
        # Daten laden
        texts, labels = classifier.preprocess_data(data_path)
        if not texts:
            logger.error(f"Keine Trainingsdaten in {args.data_dir} gefunden.")
            return

        # 1. Daten in Train und Validation splitte (90/10)
        # Wir splitten die Rohtexte und Labels, bevor wir sie encoden/tokenisieren
        texts_train, texts_val, labels_train, labels_val = train_test_split(
            texts, labels, test_size=0.1, random_state=42, stratify=labels
        )
        logger.info(f"Daten aufgeteilt: {len(texts_train)} Training, {len(texts_val)} Validation.")

        # Labels encoden (auf Basis der vollständigen Daten fitten)
        # Wenn Modell geladen wurde, prüfen wir ob die Klassen kompatibel sind
        if classifier.is_trained:
            try:
                # Versuche neue Labels mit altem Encoder zu transformieren
                classifier.label_encoder.transform(labels)
                num_classes = len(classifier.label_encoder.classes_)
                logger.info(f"Klassen sind kompatibel mit dem geladenen Modell ({num_classes} Klassen).")
            except ValueError:
                logger.info("Neue Klassen gefunden oder Reihenfolge anders. LabelEncoder wird neu gefittet.")
                classifier.label_encoder.fit(labels)
                num_classes = len(classifier.label_encoder.classes_)
                # Falls sich die Anzahl der Klassen geändert hat, markieren wir das Modell als nicht trainiert für den Reset
                classifier.is_trained = False
        else:
            classifier.label_encoder.fit(labels)
            num_classes = len(classifier.label_encoder.classes_)

        y = classifier.label_encoder.transform(labels)
        y_train = classifier.label_encoder.transform(labels_train)
        y_val = classifier.label_encoder.transform(labels_val)

        if args.method == "transformer":
            device = get_device()
            logger.info("Starte Transformer Fine-Tuning...")
            from email_classifier.engine import EmailTransformerClassifier
            import os

            if classifier.is_trained and classifier.method == "transformer":
                logger.info("Setze Training des geladenen Transformer-Modells fort.")
                # Die Gewichte sind bereits in classifier.classifier geladen
                classifier.classifier.to(device)
            else:
                logger.info("Initialisiere neues Transformer-Modell.")
                classifier.classifier = EmailTransformerClassifier(
                    args.embedding_model,
                    num_classes,
                    token=os.environ.get("HF_TOKEN")
                ).to(device)

            # Tokenisierung Training
            logger.info(f"Tokenisiere {len(texts_train)} Texte für das Training...")
            enc_train = classifier.tokenizer(texts_train, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset_train = TensorDataset(enc_train["input_ids"], enc_train["attention_mask"], torch.tensor(y_train))
            loader_train = DataLoader(dataset_train, batch_size=8, shuffle=True)

            # Tokenisierung Validation
            logger.info(f"Tokenisiere {len(texts_val)} Texte für die Validation...")
            enc_val = classifier.tokenizer(texts_val, truncation=True, padding=True, max_length=512, return_tensors="pt")
            dataset_val = TensorDataset(enc_val["input_ids"], enc_val["attention_mask"], torch.tensor(y_val))
            loader_val = DataLoader(dataset_val, batch_size=8)

            num_batches = len(loader_train)
            optimizer = torch.optim.AdamW(classifier.classifier.parameters(), lr=2e-5)
            criterion = torch.nn.CrossEntropyLoss()

            for epoch in range(3): # 3 Epochen als Standard
                classifier.classifier.train()
                logger.info(f"Starte Epoche {epoch+1}/3...")
                total_train_loss = 0
                for i, batch in enumerate(loader_train):
                    optimizer.zero_grad()
                    input_ids, mask, targets = [t.to(device) for t in batch]
                    outputs = classifier.classifier(input_ids, mask)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
                    total_train_loss += loss.item()

                    if (i + 1) % 10 == 0 or (i + 1) == num_batches:
                        current_avg_loss = total_train_loss / (i + 1)
                        logger.info(f"Epoche {epoch+1}/3, Batch {i+1}/{num_batches}, Train Loss: {current_avg_loss:.4f}")

                # Validation Loss am Ende der Epoche
                classifier.classifier.eval()
                total_val_loss = 0
                with torch.no_grad():
                    for batch in loader_val:
                        input_ids, mask, targets = [t.to(device) for t in batch]
                        outputs = classifier.classifier(input_ids, mask)
                        loss = criterion(outputs, targets)
                        total_val_loss += loss.item()

                avg_train_loss = total_train_loss / num_batches
                avg_val_loss = total_val_loss / len(loader_val)
                logger.info(f"Epoche {epoch+1}/3 abgeschlossen. Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

            classifier.is_trained = True
            cv_results = None # Keine CV für Transformer in diesem einfachen Loop
        else:
            # Merkmale extrahieren für klassische Modelle (auf VOLLSTÄNDIGEN Daten)
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
        model_file.parent.mkdir(parents=True, exist_ok=True)
        classifier.save(model_file)
        logger.info(f"Modell erfolgreich trainiert und unter {model_file} gespeichert.")

        # Evaluierung auf Trainings- und Validierungsdaten
        logger.info("Starte Evaluierung und Berichterstellung...")
        if args.method == "transformer":
            device = get_device()
            evaluate_and_save(classifier, texts_train, labels_train, model_file.parent, prefix="train", cv_results=cv_results)
            evaluate_and_save(classifier, texts_val, labels_val, model_file.parent, prefix="val")
        else:
            evaluate_and_save(classifier, texts, labels, model_file.parent, prefix="train", cv_results=cv_results)

    except Exception as e:
        logger.error(f"Fehler beim Training: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
