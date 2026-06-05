import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import torch
import numpy as np
from mcp_university.classifier.engine import EmailClassifier

@pytest.fixture
def mock_transformer_classifier():
    with patch("transformers.AutoModel.from_pretrained") as mock_model:
        with patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer:
            # Mock model configuration
            mock_model.return_value.config.hidden_size = 384
            classifier = EmailClassifier(method="transformer")
            yield classifier

def test_transformer_initialization(mock_transformer_classifier):
    assert mock_transformer_classifier.method == "transformer"
    assert mock_transformer_classifier.classifier is None

@patch("mcp_university.classifier.engine.EmailTransformerClassifier")
@patch("extract_msg.openMsg")
def test_transformer_predict(mock_open_msg, mock_nn_class, mock_transformer_classifier, tmp_path):
    # Setup mock message
    mock_msg = MagicMock()
    mock_msg.subject = "Test Subject"
    mock_msg.body = "Test Body"
    mock_msg.attachments = []
    mock_open_msg.return_value.__enter__.return_value = mock_msg

    # Setup mock NN model
    mock_nn = MagicMock()
    mock_nn_class.return_value = mock_nn
    mock_transformer_classifier.classifier = mock_nn

    # Mock label encoder
    mock_transformer_classifier.label_encoder = MagicMock()
    mock_transformer_classifier.label_encoder.classes_ = ["ClassA", "ClassB"]
    mock_transformer_classifier.label_encoder.inverse_transform.side_effect = lambda x: [["ClassA", "ClassB"][i] for i in x]
    mock_transformer_classifier.is_trained = True

    # Mock model output
    mock_output = torch.tensor([[1.0, 0.0]]) # logits
    mock_nn.return_value = mock_output

    # Mock tokenizer
    mock_transformer_classifier.tokenizer = MagicMock()
    mock_transformer_classifier.tokenizer.return_value = {
        "input_ids": torch.tensor([[1, 2, 3]]),
        "attention_mask": torch.tensor([[1, 1, 1]])
    }

    test_file = tmp_path / "test.msg"
    test_file.write_text("dummy")

    result = mock_transformer_classifier.predict(test_file)

    assert result["prediction"] == "ClassA"
    assert "ClassA" in result["probabilities"]
    assert result["confidence"] > 0.5

def test_transformer_input_formatting(mock_transformer_classifier, tmp_path):
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

        formatted = mock_transformer_classifier._format_transformer_input(test_file)

        assert "SUBJECT: Hilfe beim Projekt" in formatted
        assert "ATTACHMENTS: plan.pdf" in formatted
        assert "Ich habe eine Frage." in formatted
