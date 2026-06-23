"""Tests for tests/test_classifier_scripts_extended.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
import torch

from mcp_university.classifier.evaluate import evaluate
from mcp_university.classifier.predict import main as predict_main

@pytest.fixture
def mock_classifier():
    """Test function."""
    with patch('mcp_university.classifier.evaluate.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.label_encoder.classes_ = np.array(['Class1', 'Class2'])
        classifier_inst.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
        classifier_inst.preprocess_data.return_value = (['text1', 'text2'], ['Class1', 'Class2'])
        classifier_inst.tokenizer.return_value = {'input_ids': torch.tensor([[1]]), 'attention_mask': torch.tensor([[1]])}
        classifier_inst.method = 'transformer'
        classifier_inst.classifier = MagicMock()
        classifier_inst.classifier.return_value = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        yield classifier_inst

def test_evaluate_transformer(mock_classifier):
    """Tests test_evaluate_transformer."""
    with patch('mcp_university.classifier.evaluate.plt'),          patch('mcp_university.classifier.evaluate.sns'),          patch('mcp_university.classifier.evaluate.open', mock_open()):
        model_path = MagicMock(spec=Path)
        model_path.exists.return_value = True
        model_path.__str__.return_value = "model.pkl"
        model_path.parent = MagicMock(spec=Path)
        test_dir = MagicMock(spec=Path)
        test_dir.exists.return_value = True
        test_dir.__str__.return_value = "test_dir"
        evaluate(model_path, test_dir)
        assert mock_classifier.load.called

def test_predict_main():
    """Tests test_predict_main."""
    with patch('mcp_university.classifier.predict.EmailClassifier') as mock_cls,          patch('mcp_university.classifier.predict.argparse.ArgumentParser.parse_args') as mock_args,          patch('mcp_university.classifier.predict.resolve_model_path') as mock_resolve,          patch('mcp_university.classifier.predict.Path') as mock_path:
        mock_args.return_value = MagicMock(file_path='test.msg', model_path='model.pkl', method='transformer', mode='tfidf', json=False)
        mock_resolve.return_value.exists.return_value = True
        mock_p = MagicMock(spec=Path)
        mock_p.exists.return_value = True
        mock_p.name = 'test.msg'
        mock_path.return_value = mock_p
        classifier_inst = mock_cls.return_value
        classifier_inst.predict.return_value = {'prediction': 'C1', 'confidence': 0.9, 'probabilities': {'C1': 0.9}}
        predict_main()
        assert classifier_inst.load.called
