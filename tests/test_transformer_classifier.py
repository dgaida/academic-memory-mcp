"""Tests for tests/test_transformer_classifier.py."""
import pytest
from unittest.mock import MagicMock, patch
import torch
from mcp_university.classifier.engine import EmailClassifier

@pytest.fixture
def transformer_classifier():
    """Test function."""
    with patch("transformers.AutoModel.from_pretrained") as mock_model:
        with patch("transformers.AutoTokenizer.from_pretrained"):
            # Mock model configuration
            mock_model.return_value.config.hidden_size = 384
            classifier = EmailClassifier(method="transformer")
            yield classifier

def test_transformer_initialization(transformer_classifier):
    """Tests test_transformer_initialization."""
    assert transformer_classifier.method == "transformer"
    assert transformer_classifier.classifier is None

@patch("mcp_university.classifier.engine.EmailTransformerClassifier")
@patch("extract_msg.openMsg")
def test_transformer_predict(mock_open_msg, mock_nn_class, transformer_classifier, tmp_path):
    """Tests test_transformer_predict."""
    # Setup mock message
    mock_msg = MagicMock()
    mock_msg.subject = "Test Subject"
    mock_msg.body = "Test Body"
    mock_msg.attachments = []
    mock_open_msg.return_value.__enter__.return_value = mock_msg

    # Setup mock NN model
    mock_nn = MagicMock()
    mock_nn_class.return_value = mock_nn
    transformer_classifier.classifier = mock_nn

    # Mock label encoder
    transformer_classifier.label_encoder = MagicMock()
    transformer_classifier.label_encoder.classes_ = ["ClassA", "ClassB"]
    transformer_classifier.label_encoder.inverse_transform.side_effect = lambda x: [["ClassA", "ClassB"][i] for i in x]
    transformer_classifier.is_trained = True

    # Mock model output
    mock_output = torch.tensor([[1.0, 0.0]]) # logits
    mock_nn.return_value = mock_output

    # Mock tokenizer
    transformer_classifier.tokenizer = MagicMock()
    transformer_classifier.tokenizer.return_value = {
        "input_ids": torch.tensor([[1, 2, 3]]),
        "attention_mask": torch.tensor([[1, 1, 1]])
    }

    test_file = tmp_path / "test.msg"
    test_file.write_text("dummy")

    result = transformer_classifier.predict(test_file)

    assert result["prediction"] == "ClassA"
    assert "ClassA" in result["probabilities"]
    assert result["confidence"] > 0.5

def test_transformer_input_formatting(transformer_classifier, tmp_path):
    """Tests test_transformer_input_formatting."""
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
