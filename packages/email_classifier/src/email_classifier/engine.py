"""Engine für die Klassifizierung von E-Mails."""
from email_classifier.stopwords import ALL_STOP_WORDS
from mcp_university.config import get_config
from academic_parser.mail_parser import MailParser
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

DEFAULT_OLLAMA_EMBEDDING_MODEL = "embeddinggemma-2:270m"


def _is_ollama_embedding_model(model_name: str) -> bool:
    """Prüft, ob ein Modellname ein Ollama-Embedding-Modell bezeichnet.

    Args:
        model_name: Name oder Tag des Modells.

    Returns:
        bool: True, wenn das Modell über Ollama geladen werden soll, sonst False.
    """
    if "/" in model_name:
        return False
    if ":" in model_name:
        return True
    return model_name.startswith(
        ("embeddinggemma", "nomic-embed", "mxbai-embed", "snowflake-arctic-embed", "all-minilm")
    )


class _OllamaEmbeddingModelWrapper:
    """Adapter für Ollama-Embeddings mit `.encode()`-Schnittstelle."""

    def __init__(self, owner: "EmailClassifier") -> None:
        """Initialisiert den Adapter.

        Args:
            owner: Zugehörige EmailClassifier-Instanz.
        """
        self._owner = owner

    def encode(self, texts: List[str]) -> np.ndarray:
        """Erzeugt Embeddings für eine Liste von Texten.

        Args:
            texts: Liste der zu encodierenden Texte.

        Returns:
            np.ndarray: Matrix der Embeddings.
        """
        return self._owner.get_ollama_embeddings(texts)


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
        embedding_model_name: str = DEFAULT_OLLAMA_EMBEDDING_MODEL,
        ollama_base_url: Optional[str] = None,
    ) -> None:
        """Initialisiert den Klassifikator.

        Args:
            mode: Modus der Merkmalsextraktion ('tfidf', 'embedding', 'combined').
            method: Klassifizierungsmethode ('randomforest', 'xgboost', 'transformer').
            embedding_model_name: Name des Embedding- oder Transformer-Modells.
            ollama_base_url: Optionale Basis-URL für den Ollama-Server.
        """
        import os
        # Ensure Hugging Face Hub settings are set to prevent hanging downloads
        if "HF_HUB_DISABLE_XET" not in os.environ:
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        if "HF_HUB_DOWNLOAD_TIMEOUT" not in os.environ:
            os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "30"

        get_config()  # Sicherstellen, dass .env/.secrets geladen sind

        self.mode = mode
        self.method = method
        self.embedding_model_name = embedding_model_name
        self.ollama_base_url = ollama_base_url
        self.academic_parser = MailParser()

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
            if self.uses_ollama_embeddings:
                self.tokenizer = None
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    embedding_model_name,
                    token=os.environ.get("HF_TOKEN")
                )
        else:
            raise ValueError(f"Ungültige Klassifizierungsmethode: {method}")

        self.is_trained = False
        self._embedding_model = None

    @property
    def uses_ollama_embeddings(self) -> bool:
        """Gibt an, ob das aktuelle Modell ein Ollama-Embedding-Modell ist.

        Returns:
            bool: True bei Ollama-Embedding-Modellen, sonst False.
        """
        return _is_ollama_embedding_model(self.embedding_model_name)

    def get_ollama_embeddings(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        """Erzeugt Embeddings für Texte über die Ollama-API.

        Args:
            texts: Liste der zu encodierenden Texte.
            batch_size: Anzahl der Texte pro Ollama-Anfrage.

        Returns:
            np.ndarray: Array der Embeddings mit Shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        import ollama

        config = get_config()
        host = self.ollama_base_url or str(config.llm.base_url)
        client = ollama.Client(host=host)

        all_embeddings: List[List[float]] = []
        for start_idx in range(0, len(texts), batch_size):
            batch_texts = texts[start_idx:start_idx + batch_size]
            try:
                response = client.embed(model=self.embedding_model_name, input=batch_texts)
            except Exception as e:
                logger.error(
                    f"Fehler beim Abrufen der Ollama-Embeddings für Modell '{self.embedding_model_name}' "
                    f"unter '{host}': {e}"
                )
                raise

            batch_embeddings = (
                response.embeddings
                if hasattr(response, "embeddings")
                else response["embeddings"]
            )
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    @property
    def embedding_model(self) -> Any:
        """Lädt das Embedding-Modell verzögert (Lazy Loading)."""
        if self._embedding_model is None:
            if self.uses_ollama_embeddings:
                logger.info(f"Nutze Ollama-Embedding-Modell: {self.embedding_model_name}")
                self._embedding_model = _OllamaEmbeddingModelWrapper(self)
                return self._embedding_model

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
        return self.academic_parser.parse(file_path)

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
                return formatted
        except Exception as e:
            logger.warning(f"Error formatting transformer input for {file_path}: {e}")
            text = self._extract_text(file_path)
            return text if text else ""

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

    def _predict_neural_text(self, formatted_text: str) -> Tuple[int, np.ndarray]:
        """Führt die Vorhersage für einen formatierten Text mit dem neuronalen Modell durch.

        Args:
            formatted_text: Vorformatierter E-Mail-Text.

        Returns:
            Tuple aus vorhergesagtem Klassenindex und Wahrscheinlichkeits-Array.
        """
        device = get_device()
        self.classifier.to(device)
        self.classifier.eval()
        with torch.no_grad():
            if isinstance(self.classifier, OllamaEmbeddingClassifier) or self.uses_ollama_embeddings:
                embeddings = self.get_ollama_embeddings([formatted_text])
                embedding_tensor = torch.tensor(embeddings, dtype=torch.float32, device=device)
                outputs = self.classifier(embedding_tensor)
            else:
                inputs = self.tokenizer(
                    formatted_text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512
                )
                inputs = {k: v.to(device) for k, v in inputs.items()}
                outputs = self.classifier(inputs["input_ids"], inputs["attention_mask"])

            probs = torch.softmax(outputs, dim=1)[0]
            y_pred = int(torch.argmax(probs).item())
            y_prob = probs.cpu().numpy()
        return y_pred, y_prob

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
            y_pred, y_prob = self._predict_neural_text(text)
        else:
            text = self._extract_text(Path(file_path))
            if not text:
                raise ValueError(f"Konnte Text aus {file_path} nicht extrahieren.")
            X = self.get_features([text], train=False)
            y_pred = self.classifier.predict(X)[0]
            y_prob = self.classifier.predict_proba(X)[0]

        label = str(self.label_encoder.inverse_transform([int(y_pred)])[0])

        # Mapping von Label zu Wahrscheinlichkeit
        probs = {
            str(self.label_encoder.inverse_transform([i])[0]): float(prob)
            for i, prob in enumerate(y_prob)
        }

        return {
            "prediction": label,
            "probabilities": probs,
            "confidence": float(np.max(y_prob))
        }

    def predict_text(self, text: str) -> Dict[str, Any]:
        """Klassifiziert einen einzelnen Text (z.B. den Betreff).

        Args:
            text (str): Der zu klassifizierende Text.

        Returns:
            Dict[str, Any]: Ein Dictionary mit der vorhergesagten Klasse und Wahrscheinlichkeiten.
        """
        if not self.is_trained:
            raise RuntimeError("Modell muss zuerst trainiert oder geladen werden.")

        if self.method == "transformer":
            formatted_text = f"SUBJECT: {text} | ATTACHMENTS: None [SEP] "
            y_pred, y_prob = self._predict_neural_text(formatted_text)
        else:
            if not text:
                raise ValueError("Text darf nicht leer sein.")
            X = self.get_features([text], train=False)
            y_pred = self.classifier.predict(X)[0]
            y_prob = self.classifier.predict_proba(X)[0]

        label = str(self.label_encoder.inverse_transform([int(y_pred)])[0])

        # Mapping von Label zu Wahrscheinlichkeit
        probs = {
            str(self.label_encoder.inverse_transform([i])[0]): float(prob)
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
            # Transformer/Ollama-Embedding Modelle speichern
            is_ollama_head = isinstance(self.classifier, OllamaEmbeddingClassifier)
            config_data = {
                "model_name": self.embedding_model_name,
                "num_classes": len(self.label_encoder.classes_),
                "backbone_type": "ollama" if is_ollama_head else "huggingface",
            }
            if is_ollama_head:
                config_data["embedding_dim"] = self.classifier.embedding_dim

            classifier_data = {
                "state_dict": self.classifier.state_dict(),
                "config": config_data,
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
        try:
            data = torch.load(model_path, map_location=get_device(), weights_only=False)
        except RuntimeError as e:
            if "CUDA device" in str(e) and not torch.cuda.is_available():
                logger.error(
                    "Das Modell wurde auf einer GPU gespeichert, aber dieses System hat nur eine CPU. "
                    "Bitte speichern Sie das Modell auf dem GPU-Rechner mit der aktualisierten Version "
                    "dieses Skripts neu (welches nun 'torch.save' verwendet), damit es hardwareunabhängig "
                    "geladen werden kann."
                )
            raise e

        self.mode = data["mode"]
        self.method = data.get("method", "randomforest")  # Fallback für alte Modelle
        self.embedding_model_name = data["embedding_model_name"]
        self.tfidf_vectorizer = data["tfidf_vectorizer"]
        if self.method == "transformer":
            c_data = data["classifier"]
            import os

            saved_model_name = c_data["config"].get("model_name", self.embedding_model_name)
            backbone_type = c_data["config"].get("backbone_type")
            is_ollama_backbone = backbone_type == "ollama" or (
                backbone_type is None and _is_ollama_embedding_model(saved_model_name)
            )

            if is_ollama_backbone:
                embedding_dim = c_data["config"].get("embedding_dim")
                if embedding_dim is None and "classifier.weight" in c_data["state_dict"]:
                    embedding_dim = int(c_data["state_dict"]["classifier.weight"].shape[1])
                if embedding_dim is None:
                    raise ValueError(
                        "Konnte embedding_dim für OllamaEmbeddingClassifier nicht aus dem Checkpoint bestimmen."
                    )

                self.classifier = OllamaEmbeddingClassifier(
                    embedding_dim=embedding_dim,
                    num_classes=c_data["config"]["num_classes"],
                )
                self.classifier.load_state_dict(c_data["state_dict"])
                self.classifier.to(get_device())
                self.embedding_model_name = saved_model_name
                self.tokenizer = None
            else:
                # Robustheitsprüfung: Vergleich der gespeicherten Gewichtsdimension mit dem Modellnamen
                weight_key = "transformer.embeddings.word_embeddings.weight"
                if weight_key in c_data["state_dict"]:
                    saved_weight_shape = c_data["state_dict"][weight_key].shape
                    if len(saved_weight_shape) == 2:
                        saved_hidden_size = saved_weight_shape[1]
                        # Behebung von Konflikten zwischen mpnet (768) und MiniLM (384)
                        if saved_hidden_size == 768 and "MiniLM" in saved_model_name:
                            logger.warning(
                                f"Modellname in Konfiguration ist '{saved_model_name}' (Größe 384), "
                                f"aber die Gewichte im State-Dict haben Größe {saved_hidden_size}. "
                                "Korrigiere Modellnamen automatisch zu 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'."
                            )
                            saved_model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                        elif saved_hidden_size == 384 and "mpnet" in saved_model_name:
                            logger.warning(
                                f"Modellname in Konfiguration ist '{saved_model_name}' (Größe 768), "
                                f"aber die Gewichte im State-Dict haben Größe {saved_hidden_size}. "
                                "Korrigiere Modellnamen automatisch zu 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'."
                            )
                            saved_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

                self.classifier = EmailTransformerClassifier(
                    saved_model_name,
                    c_data["config"]["num_classes"],
                    token=os.environ.get("HF_TOKEN")
                )

                try:
                    self.classifier.load_state_dict(c_data["state_dict"])
                except RuntimeError as e:
                    logger.error(
                        f"Fehler beim Laden des State-Dicts für das Transformer-Modell: {e}\n"
                        "Dies deutet auf einen irreparablen Größenkonflikt (Size Mismatch) hin. "
                        "Bitte löschen oder benennen Sie die Modelldatei unter 'data/email_classifier_transformer.pkl' um, "
                        "und führen Sie das Training erneut aus, um ein konsistentes Modell zu erstellen."
                    )
                    raise e

                self.classifier.to(get_device())
                self.embedding_model_name = saved_model_name
                self.tokenizer = AutoTokenizer.from_pretrained(
                    saved_model_name,
                    token=os.environ.get("HF_TOKEN")
                )
        else:
            self.classifier = data["classifier"]
        self.label_encoder = data["label_encoder"]
        self.is_trained = data["is_trained"]
        # embedding_model wird bei Bedarf geladen (Lazy Loading)


class OllamaEmbeddingClassifier(nn.Module):
    """Klassifikationsmodell mit Dropout und Fully-Connected-Layer auf Ollama-Embeddings."""

    def __init__(self, embedding_dim: int, num_classes: int, dropout_rate: float = 0.1) -> None:
        """Initialisiert den Klassifikationskopf.

        Args:
            embedding_dim (int): Dimension der Eingabe-Embeddings.
            num_classes (int): Anzahl der Klassen.
            dropout_rate (float): Dropout-Wahrscheinlichkeit.
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(embedding_dim, num_classes)

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Führt den Forward-Pass auf den vorberechneten Embeddings aus.

        Args:
            embeddings (torch.Tensor): Eingabe-Embeddings der Shape (batch_size, embedding_dim).

        Returns:
            torch.Tensor: Die Modell-Logits.
        """
        dropped_embeddings = self.dropout(embeddings)
        return self.classifier(dropped_embeddings)


class EmailTransformerClassifier(nn.Module):
    """Transformer-basiertes Modell zur E-Mail-Klassifizierung."""

    def __init__(self, model_name: str, num_classes: int, token: Optional[str] = None) -> None:
        """Initialisiert das Transformer-Modell.

        Args:
            model_name (str): Name des Modells.
            num_classes (int): Anzahl der Klassen.
            token (Optional[str]): HuggingFace Token.
        """
        super().__init__()
        self.transformer = AutoModel.from_pretrained(model_name, token=token)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.transformer.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask) -> torch.Tensor:
        """Performs the forward pass of the model.

        Args:
            input_ids (torch.Tensor): Input token IDs.
            attention_mask (torch.Tensor): Attention mask.

        Returns:
            torch.Tensor: The model logits.
        """
        outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        # Use [CLS] token (first token)
        cls_output = outputs.last_hidden_state[:, 0, :]
        cls_output = self.dropout(cls_output)
        return self.classifier(cls_output)
