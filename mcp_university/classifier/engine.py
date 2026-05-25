"""Engine für die Klassifizierung von E-Mails."""

import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder


from mcp_university.parser.mail_parser import MailParser


class EmailClassifier:
    """Klassifiziert E-Mails basierend auf TF-IDF und/oder Embeddings."""

    def __init__(
        self,
        mode: str = "combined",
        method: str = "xgboost",
        embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ) -> None:
        """Initialisiert den Klassifikator.

        Args:
            mode: Modus der Merkmalsextraktion ('tfidf', 'embedding', 'combined').
            method: Klassifizierungsmethode ('randomforest', 'xgboost').
            embedding_model_name: Name des Sentence-Transformer Modells.
        """
        self.mode = mode
        self.method = method
        self.embedding_model_name = embedding_model_name
        self.parser = MailParser()

        self.tfidf_vectorizer = TfidfVectorizer(max_features=5000)
        self._embedding_model = None
        self.label_encoder = LabelEncoder()

        if method == "randomforest":
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        elif method == "xgboost":
            from xgboost import XGBClassifier

            self.classifier = XGBClassifier(
                n_estimators=100, random_state=42, eval_metric="logloss"
            )
        else:
            raise ValueError(f"Ungültige Klassifizierungsmethode: {method}")

        self.is_trained = False

    @property
    def embedding_model(self):
        """Lädt das Embedding-Modell verzögert (Lazy Loading)."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model

    def _extract_text(self, file_path: Path) -> Optional[str]:
        """Extrahiert Text aus einer E-Mail-Datei."""
        return self.parser.parse(file_path)

    def preprocess_data(
        self, root_dir: Union[str, Path]
    ) -> Tuple[List[str], List[str]]:
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
                    text = self._extract_text(file_path)
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

        text = self._extract_text(Path(file_path))
        if not text:
            raise ValueError(f"Konnte Text aus {file_path} nicht extrahieren.")

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
            "confidence": float(np.max(y_prob)),
        }

    def save(self, model_path: Union[str, Path]) -> None:
        """Speichert das Modell in einer Datei.

        Args:
            model_path: Pfad zur Speicherdatei.
        """
        data = {
            "mode": self.mode,
            "method": self.method,
            "embedding_model_name": self.embedding_model_name,
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "classifier": self.classifier,
            "label_encoder": self.label_encoder,
            "is_trained": self.is_trained,
        }
        with open(model_path, "wb") as f:
            pickle.dump(data, f)

    def load(self, model_path: Union[str, Path]) -> None:
        """Lädt das Modell aus einer Datei.

        Args:
            model_path: Pfad zur Modelldatei.
        """
        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.mode = data["mode"]
        self.method = data.get("method", "randomforest")  # Fallback für alte Modelle
        self.embedding_model_name = data["embedding_model_name"]
        self.tfidf_vectorizer = data["tfidf_vectorizer"]
        self.classifier = data["classifier"]
        self.label_encoder = data["label_encoder"]
        self.is_trained = data["is_trained"]
        # embedding_model wird bei Bedarf geladen (Lazy Loading)
