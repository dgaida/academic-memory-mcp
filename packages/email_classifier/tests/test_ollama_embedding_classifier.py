"""Tests für den E-Mail-Klassifikator mit Ollama-Embedding-Backbone."""
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import torch
import torch.nn as nn

from email_classifier.engine import (
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    EmailClassifier,
    OllamaEmbeddingClassifier,
    _is_ollama_embedding_model,
)
from email_classifier.scripts.evaluate import evaluate
from email_classifier.scripts.train import main as train_main


def test_default_embedding_model_is_ollama_embeddinggemma() -> None:
    """Prüft, dass standardmäßig das Ollama-Modell embeddinggemma-2:270m verwendet wird."""
    classifier = EmailClassifier(method="transformer")
    assert classifier.embedding_model_name == DEFAULT_OLLAMA_EMBEDDING_MODEL
    assert classifier.embedding_model_name == "embeddinggemma-2:270m"
    assert classifier.uses_ollama_embeddings is True
    assert classifier.tokenizer is None
    assert classifier.classifier is None


def test_is_ollama_embedding_model_detection() -> None:
    """Prüft die Erkennung von Ollama- vs. HuggingFace-Modellen."""
    assert _is_ollama_embedding_model("embeddinggemma-2:270m") is True
    assert _is_ollama_embedding_model("nomic-embed-text") is True
    assert _is_ollama_embedding_model("sentence-transformers/paraphrase-multilingual-mpnet-base-v2") is False
    assert _is_ollama_embedding_model("bert-base-uncased") is False


def test_ollama_embedding_classifier_head_architecture() -> None:
    """Prüft Dropout und Fully-Connected-Layer des OllamaEmbeddingClassifier."""
    model = OllamaEmbeddingClassifier(embedding_dim=768, num_classes=3, dropout_rate=0.1)
    assert isinstance(model.dropout, nn.Dropout)
    assert isinstance(model.classifier, nn.Linear)
    assert model.classifier.in_features == 768
    assert model.classifier.out_features == 3

    inputs = torch.randn(4, 768)
    outputs = model(inputs)
    assert outputs.shape == (4, 3)


def test_get_ollama_embeddings_batching() -> None:
    """Prüft das batchweise Abrufen von Embeddings über ollama.Client.embed."""
    classifier = EmailClassifier(method="transformer", ollama_base_url="http://localhost:11434")

    mock_client = MagicMock()
    mock_client.embed.side_effect = [
        MagicMock(embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
        MagicMock(embeddings=[[0.7, 0.8, 0.9]]),
    ]

    with patch("ollama.Client", return_value=mock_client) as mock_client_cls:
        result = classifier.get_ollama_embeddings(["t1", "t2", "t3"], batch_size=2)

    mock_client_cls.assert_called_once_with(host="http://localhost:11434")
    assert mock_client.embed.call_count == 2
    assert result.shape == (3, 3)
    assert result.dtype == np.float32


def test_predict_and_predict_text_with_ollama_head(tmp_path: Path) -> None:
    """Prüft predict und predict_text mit dem OllamaEmbeddingClassifier."""
    classifier = EmailClassifier(method="transformer")
    classifier.label_encoder.fit(["BachelorThesis", "Other"])
    classifier.classifier = OllamaEmbeddingClassifier(embedding_dim=4, num_classes=2)
    classifier.is_trained = True

    with torch.no_grad():
        classifier.classifier.classifier.weight.zero_()
        classifier.classifier.classifier.bias.copy_(torch.tensor([5.0, -5.0]))

    msg_file = tmp_path / "mail.msg"
    msg_file.write_text("dummy", encoding="utf-8")

    with patch.object(classifier, "_format_transformer_input", return_value="SUBJECT: Test | ATTACHMENTS: None [SEP] Hallo"), \
         patch.object(classifier, "get_ollama_embeddings", return_value=np.ones((1, 4), dtype=np.float32)) as mock_emb:
        file_result = classifier.predict(msg_file)
        text_result = classifier.predict_text("Test Betreff")

    assert mock_emb.call_count == 2
    assert file_result["prediction"] == "BachelorThesis"
    assert text_result["prediction"] == "BachelorThesis"
    assert file_result["confidence"] > 0.99


def test_save_and_load_ollama_classifier_roundtrip(tmp_path: Path) -> None:
    """Prüft Speichern und Laden eines trainierten OllamaEmbeddingClassifier."""
    model_path = tmp_path / "email_classifier_transformer.pkl"

    classifier = EmailClassifier(method="transformer")
    classifier.label_encoder.fit(["ClassA", "ClassB"])
    classifier.classifier = OllamaEmbeddingClassifier(embedding_dim=8, num_classes=2)
    classifier.is_trained = True
    classifier.save(model_path)

    loaded = EmailClassifier()
    with patch("transformers.AutoTokenizer.from_pretrained") as mock_tok, \
         patch("transformers.AutoModel.from_pretrained") as mock_auto_model:
        loaded.load(model_path)

    mock_tok.assert_not_called()
    mock_auto_model.assert_not_called()
    assert loaded.method == "transformer"
    assert loaded.embedding_model_name == "embeddinggemma-2:270m"
    assert loaded.tokenizer is None
    assert isinstance(loaded.classifier, OllamaEmbeddingClassifier)
    assert loaded.classifier.embedding_dim == 8
    assert loaded.classifier.num_classes == 2
    assert loaded.is_trained is True


def test_train_main_with_default_ollama_model(tmp_path: Path) -> None:
    """Prüft train_main mit dem Standard-Ollama-Embedding-Modell."""
    data_dir = tmp_path / "train_data"
    data_dir.mkdir()
    model_path = tmp_path / "out" / "email_classifier.pkl"
    resolved_model_path = tmp_path / "out" / "email_classifier_transformer.pkl"

    texts = [f"SUBJECT: Mail {i} | ATTACHMENTS: None [SEP] Body {i}" for i in range(20)]
    labels = ["ClassA" if i % 2 == 0 else "ClassB" for i in range(20)]

    mock_client = MagicMock()
    mock_client.embed.side_effect = lambda model, input: MagicMock(
        embeddings=[[float(idx + 1), 0.5, 0.25, 0.1] for idx, _ in enumerate(input)]
    )

    with patch("sys.argv", ["train.py", str(data_dir), "--model-path", str(model_path)]), \
         patch("email_classifier.engine.EmailClassifier.preprocess_data", return_value=(texts, labels)), \
         patch("ollama.Client", return_value=mock_client), \
         patch("email_classifier.scripts.train.evaluate_and_save") as mock_eval_save:
        train_main()

    assert resolved_model_path.exists()
    assert mock_eval_save.call_count == 2


def test_evaluate_with_ollama_model(tmp_path: Path) -> None:
    """Prüft evaluate.py mit einem gespeicherten OllamaEmbeddingClassifier."""
    model_path = tmp_path / "email_classifier_transformer.pkl"
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()

    classifier = EmailClassifier(method="transformer")
    classifier.label_encoder.fit(["ClassA", "ClassB"])
    classifier.classifier = OllamaEmbeddingClassifier(embedding_dim=4, num_classes=2)
    classifier.is_trained = True
    classifier.save(model_path)

    mock_client = MagicMock()
    mock_client.embed.return_value = MagicMock(
        embeddings=[[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]]
    )

    with patch("email_classifier.engine.EmailClassifier.preprocess_data", return_value=(["t1", "t2"], ["ClassA", "ClassB"])), \
         patch("ollama.Client", return_value=mock_client):
        evaluate(model_path, test_dir)

    assert (tmp_path / "test_confusion_matrix.png").exists()
    assert (tmp_path / "test_metrics.md").exists()
