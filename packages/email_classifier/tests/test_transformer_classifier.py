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
            mock_model.return_value.config.hidden_size = 384

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
