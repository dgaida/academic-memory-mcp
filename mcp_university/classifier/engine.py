"""Engine für die Klassifizierung von E-Mails."""
from mcp_university.classifier.stopwords import ALL_STOP_WORDS
from mcp_university.config import get_config
from mcp_university.parser.mail_parser import MailParser
from mcp_university.utils.anonymizer import anonymize_th_koeln_names
from mcp_university.utils.torch_utils import get_device
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from transformers import AutoModel, AutoTokenizer
from typing import List, Tuple, Dict, Any, Optional, Union
import logging
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


def resolve_model_path(base_path: Union[str, Path], method: str, mode: str) -> Path:
    """Erstellt den vollständigen Modellpfad basierend auf Methode und Modus.

    Args:
        base_path: Basis-Pfad (z.B. data/email_classifier.pkl).
        method: Klassifizierungsmethode (transformer, xgboost, randomforest).
        mode: Merkmalsextraktion (tfidf, embedding, combined).

    Returns:
        Vollständiger Pfad als Path-Objekt.
    """
    path = Path(base_path)
    if method == "transformer":
        suffix = "_transformer"
    else:
        suffix = f"_{method}_{mode}"

    # Suffix anhängen, falls noch nicht vorhanden
    if suffix not in path.stem:
        # Alte Suffixe entfernen, falls vorhanden (um Dopplungen zu vermeiden)
        stem = path.stem
        for m in ["_tfidf", "_embedding", "_combined", "_transformer", "_xgboost", "_randomforest"]:
            if stem.endswith(m):
                stem = stem[:-len(m)]
        # Den Suffix gezielt anhängen
        path = path.with_name(f"{stem}{suffix}{path.suffix}")
    return path


class EmailClassifier:
    """Klassifiziert E-Mails basierend auf TF-IDF und/oder Embeddings."""

    def __init__(
        self,
        mode: str = "combined",
        method: str = "xgboost",
        embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ) -> None:
        """Initialisiert den Klassifikator.

        Args:
            mode: Modus der Merkmalsextraktion ('tfidf', 'embedding', 'combined').
            method: Klassifizierungsmethode ('randomforest', 'xgboost', 'transformer').
            embedding_model_name: Name des Sentence-Transformer Modell.
        """
        import os
        get_config()  # Sicherstellen, dass .env/.secrets geladen sind

        self.mode = mode
        self.method = method
        self.embedding_model_name = embedding_model_name
        self.parser = MailParser()

        # TF-IDF Vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=list(ALL_STOP_WORDS),
            token_pattern=r"(?u)\b(?!\d{2}\b)[a-zA-ZäöüÄÖÜß0-9]{2,}\b",
            sublinear_tf=False
        )

        # Label Encoder
        self.label_encoder = LabelEncoder()

        # Klassifikator initialisieren
        if method == "randomforest":
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        elif method == "xgboost":
            from xgboost import XGBClassifier
            self.classifier = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
        elif method == "transformer":
            self.classifier = None  # Wird im Training oder beim Laden initialisiert
            self.tokenizer = AutoTokenizer.from_pretrained(
                embedding_model_name,
                token=os.environ.get("HF_TOKEN")
            )
        else:
            raise ValueError(f"Ungültige Klassifizierungsmethode: {method}")

        self.is_trained = False
        self._embedding_model = None

    @property
    def embedding_model(self) -> Any:
        """Lädt das Embedding-Modell verzögert (Lazy Loading)."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            import os
            config = get_config()

            try:
                # Versuch 1: Nur lokale Dateien (verhindert HEAD-Requests an HF)
                logger.info(f"Versuche Embedding-Modell lokal zu laden: {self.embedding_model_name}")
                self._embedding_model = SentenceTransformer(self.embedding_model_name, local_files_only=True)
                logger.info(f"ERFOLG: Modell {self.embedding_model_name} wurde LOKAL geladen.")
            except Exception as e:
                if config.offline:
                    logger.error(f"Modell {self.embedding_model_name} nicht lokal gefunden und Offline-Modus ist aktiv: {e}")
                    raise

                # Versuch 2: Normales Laden (erlaubt Download), falls nicht im strikten Offline-Modus
                logger.info(f"Modell nicht lokal gefunden. Lade von Hugging Face: {self.embedding_model_name}")
                self._embedding_model = SentenceTransformer(
                    self.embedding_model_name,
                    token=os.environ.get("HF_TOKEN")
                )
        return self._embedding_model

    def _extract_text(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer E-Mail-Datei."""
        return self.parser.parse(file_path)

    def _format_transformer_input(self, file_path: Path) -> str:
        """Formatiert die E-Mail-Komponenten für den Transformer-Input."""
        try:
            import extract_msg
            with extract_msg.openMsg(str(file_path)) as msg:
                subject = msg.subject or '(No Subject)'
                body = msg.body or ''
                attachment_names = []
                for att in msg.attachments:
                    name = None
                    if hasattr(att, "getFilename"):
                        try:
                            name = att.getFilename()
                        except Exception:
                            pass
                    if not name:
                        name = getattr(att, "name", None) or getattr(att, "longFilename", None)
                    if name:
                        attachment_names.append(name)

                attachments_str = ", ".join(attachment_names) if attachment_names else "None"
                formatted = f"SUBJECT: {subject} | ATTACHMENTS: {attachments_str} [SEP] {body}"
                return anonymize_th_koeln_names(formatted)
        except Exception as e:
            logger.warning(f"Error formatting transformer input for {file_path}: {e}")
            text = self._extract_text(file_path)
            return anonymize_th_koeln_names(text) if text else ""

    def preprocess_data(self, root_dir: Union[str, Path]) -> Tuple[List[str], List[str]]:
        """Liest E-Mails aus Ordnerstrukturen ein.

        Die Ordnernamen werden als Klassenlabels verwendet.

        Args:
            root_dir: Wurzelverzeichnis mit Unterordnern für jede Klasse.

        Returns:
            Tuple aus Texten und Labels.
        """
        root_path = Path(root_dir)
        texts = []
        labels = []

        for class_dir in root_path.iterdir():
            if class_dir.is_dir():
                label = class_dir.name
                for file_path in class_dir.rglob("*.msg"):
                    if self.method == "transformer":
                        text = self._format_transformer_input(file_path)
                    else:
                        text = self._extract_text(file_path)
                        if text:
                            text = anonymize_th_koeln_names(text)

                    if text:
                        texts.append(text)
                        labels.append(label)

        return texts, labels

    def get_features(self, texts: List[str], train: bool = False) -> np.ndarray:
        """Extrahiert Merkmale aus Texten basierend auf dem gewählten Modus."""
        features = []

        if self.mode in ["tfidf", "combined"]:
            if train:
                tfidf_feats = self.tfidf_vectorizer.fit_transform(texts).toarray()
            else:
                tfidf_feats = self.tfidf_vectorizer.transform(texts).toarray()
            features.append(tfidf_feats)

        if self.mode in ["embedding", "combined"]:
            emb_feats = self.embedding_model.encode(texts)
            features.append(emb_feats)

        if len(features) > 1:
            return np.hstack(features)
        return features[0]

    def train(self, root_dir: Union[str, Path]) -> None:
        """Trainiert den Klassifikator auf Daten aus einem Verzeichnis.

        Args:
            root_dir: Verzeichnis mit den Trainingsdaten.
        """
        texts, labels = self.preprocess_data(root_dir)
        if not texts:
            raise ValueError(f"Keine Trainingsdaten in {root_dir} gefunden.")

        X = self.get_features(texts, train=True)
        y = self.label_encoder.fit_transform(labels)

        self.classifier.fit(X, y)
        self.is_trained = True

    def predict(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Klassifiziert eine einzelne E-Mail.

        Args:
            file_path: Pfad zur .msg Datei.

        Returns:
            Dictionary mit der vorhergesagten Klasse und Wahrscheinlichkeiten.
        """
        if not self.is_trained:
            raise RuntimeError("Modell muss zuerst trainiert oder geladen werden.")

        if self.method == "transformer":
            text = self._format_transformer_input(Path(file_path))
            device = get_device()
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            self.classifier.to(device)
            self.classifier.eval()
            with torch.no_grad():
                outputs = self.classifier(inputs["input_ids"], inputs["attention_mask"])
                probs = torch.softmax(outputs, dim=1)[0]
                y_pred = torch.argmax(probs).item()
                y_prob = probs.cpu().numpy()
        else:
            text = self._extract_text(Path(file_path))
            if not text:
                raise ValueError(f"Konnte Text aus {file_path} nicht extrahieren.")
            text = anonymize_th_koeln_names(text)
            X = self.get_features([text], train=False)
            y_pred = self.classifier.predict(X)[0]
            y_prob = self.classifier.predict_proba(X)[0]

        label = self.label_encoder.inverse_transform([int(y_pred)])[0]

        # Mapping von Label zu Wahrscheinlichkeit
        probs = {
            self.label_encoder.inverse_transform([i])[0]: float(prob)
            for i, prob in enumerate(y_prob)
        }

        return {
            "prediction": label,
            "probabilities": probs,
            "confidence": float(np.max(y_prob))
        }

    def save(self, model_path: Union[str, Path]) -> None:
        """Speichert das Modell in einer Datei.

        Args:
            model_path: Pfad zur Speicherdatei.
        """
        if self.method == "transformer":
            # Transformer Modelle separat speichern oder State Dict nutzen
            classifier_data = {
                "state_dict": self.classifier.state_dict(),
                "config": {
                    "model_name": self.embedding_model_name,
                    "num_classes": len(self.label_encoder.classes_)
                }
            }
        else:
            classifier_data = self.classifier

        data = {
            "mode": self.mode,
            "method": self.method,
            "embedding_model_name": self.embedding_model_name,
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "classifier": classifier_data,
            "label_encoder": self.label_encoder,
            "is_trained": self.is_trained
        }
        torch.save(data, model_path)

    def load(self, model_path: Union[str, Path]) -> None:
        """Lädt das Modell aus einer Datei.

        Args:
            model_path: Pfad zur Modelldatei.
        """
        data = torch.load(model_path, map_location=get_device(), weights_only=False)

        self.mode = data["mode"]
        self.method = data.get("method", "randomforest")  # Fallback für alte Modelle
        self.embedding_model_name = data["embedding_model_name"]
        self.tfidf_vectorizer = data["tfidf_vectorizer"]
        if self.method == "transformer":
            c_data = data["classifier"]
            import os
            self.classifier = EmailTransformerClassifier(
                c_data["config"]["model_name"],
                c_data["config"]["num_classes"],
                token=os.environ.get("HF_TOKEN")
            )
            self.classifier.load_state_dict(c_data["state_dict"])
            self.classifier.to(get_device())
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.embedding_model_name,
                token=os.environ.get("HF_TOKEN")
            )
        else:
            self.classifier = data["classifier"]
        self.label_encoder = data["label_encoder"]
        self.is_trained = data["is_trained"]
        # embedding_model wird bei Bedarf geladen (Lazy Loading)


class EmailTransformerClassifier(nn.Module):
    """Transformer-basiertes Modell zur E-Mail-Klassifizierung."""

    def __init__(self, model_name: str, num_classes: int, token: Optional[str] = None) -> None:
        super().__init__()
        self.transformer = AutoModel.from_pretrained(model_name, token=token)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.transformer.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask) -> torch.Tensor:
        outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        # Use [CLS] token (first token)
        cls_output = outputs.last_hidden_state[:, 0, :]
        cls_output = self.dropout(cls_output)
        return self.classifier(cls_output)
