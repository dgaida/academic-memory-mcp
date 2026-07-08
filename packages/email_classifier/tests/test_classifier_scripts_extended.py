"""Tests for test_classifier_scripts_extended.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
import numpy as np
import torch
from email_classifier.scripts.evaluate import evaluate

@pytest.fixture
def mock_classifier():
    """Test function docstring."""
    with patch('email_classifier.scripts.evaluate.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.label_encoder.classes_ = np.array(['Class1', 'Class2'])
        classifier_inst.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
        classifier_inst.preprocess_data.return_value = (['text1', 'text2'], ['Class1', 'Class2'])
        classifier_inst.tokenizer.side_effect = lambda *args, **kwargs: {'input_ids': torch.zeros((len(args[0]), 1)), 'attention_mask': torch.ones((len(args[0]), 1))}
        classifier_inst.method = 'transformer'

        mock_nn = MagicMock()
        mock_nn.side_effect = lambda *args, **kwargs: torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        classifier_inst.classifier = mock_nn

        yield classifier_inst

def test_evaluate_transformer(mock_classifier):
    """Test function docstring."""
    with patch('matplotlib.pyplot.savefig'), patch('matplotlib.pyplot.show'), patch('matplotlib.pyplot.close'),                    patch('email_classifier.scripts.evaluate.open', mock_open()):

        model_path = MagicMock()
        model_path.exists.return_value = True
        model_path.__str__.return_value = "model.pkl"
        model_path.parent = MagicMock()

        test_dir = MagicMock()
        test_dir.exists.return_value = True

        evaluate(model_path, test_dir)
        assert mock_classifier.load.called
