"""Tests for test_transformer_classifier.py."""
import pytest
from unittest.mock import MagicMock, patch

from email_classifier.engine import EmailClassifier

@pytest.fixture
def transformer_classifier():
    """Test function docstring."""
    with patch("transformers.AutoModel.from_pretrained") as mock_model:
        with patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer:
            # Mock model configuration
            mock_model.return_value.config.hidden_size = 768

            # Create a mock tokenizer class and instance
            mock_tok_inst = MagicMock()
            # Set __class__.__name__ to satisfy transformers' internal checks
            type(mock_tok_inst).__name__ = "PreTrainedTokenizerFast"
            mock_tokenizer.return_value = mock_tok_inst

            classifier = EmailClassifier(method="transformer")
            yield classifier

def test_transformer_initialization(transformer_classifier):
    """Test function docstring."""
    assert transformer_classifier.method == "transformer"
    assert transformer_classifier.classifier is None

def test_transformer_input_formatting(transformer_classifier, tmp_path):
    """Test function docstring."""
    with patch("extract_msg.openMsg") as mock_open_msg:
        mock_msg = MagicMock()
        mock_msg.subject = "Hilfe beim Projekt"
        mock_msg.body = "Ich habe eine Frage."
        mock_att = MagicMock()
        mock_att.getFilename.return_value = "plan.pdf"
        mock_msg.attachments = [mock_att]
        mock_open_msg.return_value.__enter__.return_value = mock_msg

        test_file = tmp_path / "test.msg"
        test_file.write_text("dummy")

        formatted = transformer_classifier._format_transformer_input(test_file)

        assert "SUBJECT: Hilfe beim Projekt" in formatted
        assert "ATTACHMENTS: plan.pdf" in formatted
        assert "Ich habe eine Frage." in formatted


def test_transformer_input_no_anonymization(transformer_classifier, tmp_path):
    """Verify that formatting transformer input does not use rule-based anonymization for local models."""
    with patch("extract_msg.openMsg") as mock_open_msg:
        mock_msg = MagicMock()
        mock_msg.subject = "Frage von Sibel"
        mock_msg.body = "Hallo Herr Gaida, mein Name ist Sibel Sözer."
        mock_msg.attachments = []
        mock_open_msg.return_value.__enter__.return_value = mock_msg

        test_file = tmp_path / "test_no_anon.msg"
        test_file.touch()

        formatted = transformer_classifier._format_transformer_input(test_file)

        # It must preserve "Sibel Sözer", not replace it with "Max Mustermann"
        assert "Sibel Sözer" in formatted
        assert "Max Mustermann" not in formatted


def test_load_mismatch_auto_correction(tmp_path):
    """Test that size mismatch between state_dict weights and model_name is auto-corrected on load."""
    model_file = tmp_path / "test_model.pkl"

    # Mock data to load
    mock_data = {
        "mode": "combined",
        "method": "transformer",
        "embedding_model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "tfidf_vectorizer": MagicMock(),
        "label_encoder": MagicMock(),
        "is_trained": True,
        "classifier": {
            "config": {
                "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "num_classes": 2
            },
            "state_dict": {
                # Word embeddings weight has shape representing mpnet-base (768)
                "transformer.embeddings.word_embeddings.weight": MagicMock(shape=(250002, 768))
            }
        }
    }
    mock_data["label_encoder"].classes_ = ["Class1", "Class2"]

    with patch("torch.load", return_value=mock_data), \
         patch("transformers.AutoModel.from_pretrained") as mock_model, \
         patch("transformers.AutoTokenizer.from_pretrained") as mock_tok, \
         patch("email_classifier.engine.EmailTransformerClassifier.load_state_dict") as mock_load_state_dict:

        mock_model.return_value.config.hidden_size = 768
        mock_tok_inst = MagicMock()
        type(mock_tok_inst).__name__ = "PreTrainedTokenizerFast"
        mock_tok.return_value = mock_tok_inst

        classifier = EmailClassifier(method="transformer")
        classifier.load(model_file)

        # Check that model name was auto-corrected to mpnet-base-v2
        assert classifier.embedding_model_name == "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        mock_load_state_dict.assert_called_once_with(mock_data["classifier"]["state_dict"])
