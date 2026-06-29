"""Tests for test_classifier_scripts_extended.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
import torch
from email_classifier.evaluate import evaluate

@pytest.fixture
def mock_classifier():
    """Test function docstring."""
    with patch('email_classifier.evaluate.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.label_encoder.classes_ = np.array(['Class1', 'Class2'])
        classifier_inst.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
        classifier_inst.preprocess_data.return_value = (['text1', 'text2'], ['Class1', 'Class2'])
        classifier_inst.tokenizer.return_value = {'input_ids': torch.tensor([[1]]), 'attention_mask': torch.tensor([[1]])}
        classifier_inst.method = 'transformer'

        mock_nn = MagicMock()
        mock_nn.return_value = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        classifier_inst.classifier = mock_nn

        yield classifier_inst

def test_evaluate_transformer(mock_classifier):
    """Test function docstring."""
    with patch('email_classifier.evaluate.plt'),          patch('email_classifier.evaluate.sns'),          patch('email_classifier.evaluate.open', mock_open()):

        model_path = MagicMock(spec=Path)
        model_path.exists.return_value = True
        model_path.__str__.return_value = "model.pkl"
        model_path.parent = MagicMock(spec=Path)

        test_dir = MagicMock(spec=Path)
        test_dir.exists.return_value = True

        evaluate(model_path, test_dir)
        assert mock_classifier.load.called
