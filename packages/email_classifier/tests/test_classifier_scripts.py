"""Tests for test_classifier_scripts.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
import torch

# We will import these inside tests to ensure they are tracked by coverage if needed,
# though normally top-level import is fine with pytest-cov.
from email_classifier.scripts.evaluate import evaluate, main as evaluate_main
from email_classifier.scripts.predict import main as predict_main

@pytest.fixture
def mock_classifier():
    """Test function docstring."""
    with patch('email_classifier.scripts.evaluate.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.label_encoder.classes_ = np.array(['Class1', 'Class2'])
        classifier_inst.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
        classifier_inst.preprocess_data.return_value = (['text1', 'text2'], ['Class1', 'Class2'])
        classifier_inst.tokenizer.side_effect = lambda *args, **kwargs: {'input_ids': torch.tensor([[1]]), 'attention_mask': torch.tensor([[1]])}
        classifier_inst.method = 'transformer'

        # Mock the classifier as a callable that returns a tensor
        mock_nn = MagicMock()
        mock_nn.return_value = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        classifier_inst.classifier = mock_nn

        yield classifier_inst

def test_evaluate_transformer(mock_classifier):
    """Test function docstring."""
    with patch('email_classifier.scripts.evaluate.plt'),          patch('email_classifier.scripts.evaluate.sns'),          patch('email_classifier.scripts.evaluate.open', mock_open()) as _mock_file:
        
        model_path = MagicMock(spec=Path)
        model_path.exists.return_value = True
        model_path.__str__.return_value = "model.pkl"
        model_path.parent = MagicMock(spec=Path)
        model_path.parent.mkdir.return_value = None
        # Ensure mkdir works
        model_path.parent.__truediv__.return_value = MagicMock(spec=Path)
        
        test_dir = MagicMock(spec=Path)
        test_dir.exists.return_value = True
        test_dir.__str__.return_value = "test_dir"
        
        evaluate(model_path, test_dir)
        
        assert mock_classifier.load.called
        assert mock_classifier.preprocess_data.called

def test_evaluate_non_transformer(mock_classifier):
    """Test function docstring."""
    mock_classifier.method = 'randomforest'
    # For non-transformer, it calls predict() on the classifier member
    mock_classifier.classifier.predict.return_value = np.array([0, 1])
    
    with patch('email_classifier.scripts.evaluate.plt'),          patch('email_classifier.scripts.evaluate.sns'),          patch('email_classifier.scripts.evaluate.open', mock_open()):
        
        model_path = MagicMock(spec=Path)
        model_path.exists.return_value = True
        model_path.__str__.return_value = "model.pkl"
        model_path.parent = MagicMock(spec=Path)
        model_path.parent.mkdir.return_value = None
        model_path.parent.__truediv__.return_value = MagicMock(spec=Path)
        
        test_dir = MagicMock(spec=Path)
        test_dir.exists.return_value = True
        test_dir.__str__.return_value = "test_dir"
        
        evaluate(model_path, test_dir)
        
        assert mock_classifier.get_features.called

def test_evaluate_missing_paths(mock_classifier):
    """Test function docstring."""
    model_path = MagicMock(spec=Path)
    model_path.exists.return_value = False
    test_dir = MagicMock(spec=Path)
    test_dir.exists.return_value = True
    
    evaluate(model_path, test_dir)
    assert not mock_classifier.load.called
    
    model_path.exists.return_value = True
    test_dir.exists.return_value = False
    evaluate(model_path, test_dir)
    assert not mock_classifier.load.called

def test_evaluate_no_data(mock_classifier):
    """Test function docstring."""
    mock_classifier.preprocess_data.return_value = ([], [])
    model_path = MagicMock(spec=Path)
    model_path.exists.return_value = True
    test_dir = MagicMock(spec=Path)
    test_dir.exists.return_value = True
    
    evaluate(model_path, test_dir)
    assert mock_classifier.load.called

def test_evaluate_main():
    """Test function docstring."""
    with patch('email_classifier.scripts.evaluate.argparse.ArgumentParser.parse_args') as mock_args,          patch('email_classifier.scripts.evaluate.resolve_model_path') as mock_resolve,          patch('email_classifier.scripts.evaluate.evaluate') as mock_evaluate:
        
        mock_args.return_value = MagicMock(test_dir='test', model_path='model', method='transformer', mode='combined')
        mock_resolve.return_value = Path('resolved_model')
        
        evaluate_main()
        mock_evaluate.assert_called_once()

# Tests for predict.py

@pytest.fixture
def mock_predict_classifier():
    """Test function docstring."""
    with patch('email_classifier.scripts.predict.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.predict.return_value = {
            'prediction': 'Class1',
            'confidence': 0.95,
            'probabilities': {'Class1': 0.95, 'Class2': 0.05}
        }
        yield classifier_inst

def test_predict_main(mock_predict_classifier):
    """Test function docstring."""
    with patch('email_classifier.scripts.predict.argparse.ArgumentParser.parse_args') as mock_args,          patch('email_classifier.scripts.predict.resolve_model_path') as mock_resolve,          patch('email_classifier.scripts.predict.Path') as mock_path:
        
        mock_args.return_value = MagicMock(file_path='test.msg', model_path='model.pkl', method='transformer', mode='tfidf', json=False)
        mock_resolve.return_value.exists.return_value = True
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.name = 'test.msg'
        # Mocking the instance returned by Path(args.file_path)
        mock_path.side_effect = lambda x: MagicMock(spec=Path, exists=lambda: True, name=x) if isinstance(x, str) else x
        
        predict_main()
        assert mock_predict_classifier.load.called
        assert mock_predict_classifier.predict.called

def test_predict_main_json(mock_predict_classifier):
    """Test function docstring."""
    with patch('email_classifier.scripts.predict.argparse.ArgumentParser.parse_args') as mock_args,          patch('email_classifier.scripts.predict.resolve_model_path') as mock_resolve,          patch('email_classifier.scripts.predict.Path') as mock_path,          patch('builtins.print') as mock_print:
        
        mock_args.return_value = MagicMock(file_path='test.msg', model_path='model.pkl', method='transformer', mode='tfidf', json=True)
        mock_resolve.return_value.exists.return_value = True
        mock_path.return_value.exists.return_value = True
        mock_path.side_effect = lambda x: MagicMock(spec=Path, exists=lambda: True, name=x) if isinstance(x, str) else x
        
        predict_main()
        mock_print.assert_called()

def test_predict_main_missing_file(mock_predict_classifier):
    """Test function docstring."""
    with patch('email_classifier.scripts.predict.argparse.ArgumentParser.parse_args') as mock_args,          patch('email_classifier.scripts.predict.resolve_model_path') as mock_resolve,          patch('email_classifier.scripts.predict.Path') as mock_path:
        
        mock_args.return_value = MagicMock(file_path='test.msg', model_path='model.pkl', method='transformer', mode='tfidf', json=False)
        mock_resolve.return_value.exists.return_value = True
        # Create a mock path that reports it doesn't exist
        mock_p = MagicMock(spec=Path)
        mock_p.exists.return_value = False
        mock_path.return_value = mock_p
        
        predict_main()
        assert not mock_predict_classifier.load.called
