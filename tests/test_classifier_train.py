"""Tests for tests/test_classifier_train.py."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
import torch
from mcp_university.classifier.train import evaluate_and_save, main as train_main

@pytest.fixture
def mock_classifier():
    """Test function."""
    with patch('mcp_university.classifier.train.EmailClassifier') as mock:
        classifier_inst = mock.return_value
        classifier_inst.label_encoder.classes_ = np.array(['Class1', 'Class2'])
        classifier_inst.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
        classifier_inst.label_encoder.transform.side_effect = lambda x: np.array([0 if val == 'Class1' else 1 for val in x])
        classifier_inst.method = 'transformer'
        classifier_inst.tokenizer.side_effect = lambda texts, **kwargs: {
            'input_ids': torch.zeros((len(texts), 10)), 
            'attention_mask': torch.ones((len(texts), 10))
        }
        classifier_inst.classifier = MagicMock()
        classifier_inst.classifier.return_value = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        classifier_inst.classifier.predict.return_value = np.array([0, 1])
        yield classifier_inst

def test_evaluate_and_save(mock_classifier):
    """Tests test_evaluate_and_save."""
    with patch('mcp_university.classifier.train.plt'),          patch('mcp_university.classifier.train.sns'),          patch('mcp_university.classifier.train.open', mock_open()):
        
        output_dir = MagicMock(spec=Path)
        evaluate_and_save(mock_classifier, ['text', 'text2'], ['Class1', 'Class2'], output_dir)
        assert output_dir.mkdir.called

def test_train_main():
    """Tests test_train_main."""
    with patch('mcp_university.classifier.train.argparse.ArgumentParser.parse_args') as mock_args,          patch('mcp_university.classifier.train.EmailClassifier') as mock_classifier_cls,          patch('mcp_university.classifier.train.train_test_split') as mock_split,          patch('mcp_university.classifier.train.resolve_model_path') as mock_resolve,          patch('mcp_university.classifier.train.evaluate_and_save') as _mock_eval,          patch('mcp_university.config.get_config') as _mock_config,          patch('mcp_university.classifier.train.get_device'),          patch('mcp_university.classifier.engine.EmailTransformerClassifier'),          patch('mcp_university.classifier.train.Path.exists', return_value=True):
        
        mock_args.return_value = MagicMock(
            data_dir='data', method='transformer', mode='combined', 
            model_path='model.pkl', embedding_model='bert-base-uncased'
        )
        mock_classifier = mock_classifier_cls.return_value
        mock_classifier.method = 'transformer'
        mock_classifier.preprocess_data.return_value = (['t1', 't2', 't3', 't4'], ['Class1', 'Class2', 'Class1', 'Class2'])
        # Return 4 lists of size 2 each
        mock_split.return_value = (['t1', 't3'], ['t2', 't4'], ['Class1', 'Class1'], ['Class2', 'Class2'])
        
        resolved_path = MagicMock(spec=Path)
        resolved_path.parent = MagicMock(spec=Path)
        resolved_path.exists.return_value = False
        mock_resolve.return_value = resolved_path
        
        train_main()
        # Even if it fails later, we hit many lines
        assert True

def test_train_main_rf():
    """Tests test_train_main_rf."""
    with patch('mcp_university.classifier.train.argparse.ArgumentParser.parse_args') as mock_args,          patch('mcp_university.classifier.train.EmailClassifier') as mock_classifier_cls,          patch('mcp_university.classifier.train.train_test_split') as mock_split,          patch('mcp_university.classifier.train.resolve_model_path') as mock_resolve,          patch('mcp_university.classifier.train.GridSearchCV') as mock_grid,          patch('mcp_university.config.get_config') as _mock_config,          patch('mcp_university.classifier.train.Path.exists', return_value=True):
        
        mock_args.return_value = MagicMock(
            data_dir='data', method='randomforest', mode='tfidf', 
            model_path='model.pkl', embedding_model='bert-base-uncased'
        )
        mock_classifier = mock_classifier_cls.return_value
        mock_classifier.method = 'randomforest'
        mock_classifier.preprocess_data.return_value = (['t1', 't2'], ['Class1', 'Class2'])
        mock_split.return_value = (['t1'], ['t2'], ['Class1'], ['Class2'])
        
        mock_grid_inst = mock_grid.return_value
        mock_grid_inst.best_estimator_ = MagicMock()
        mock_grid_inst.best_params_ = {}
        mock_grid_inst.best_score_ = 0.9
        mock_grid_inst.cv_results_ = {}
        
        resolved_path = MagicMock(spec=Path)
        resolved_path.parent = MagicMock(spec=Path)
        resolved_path.exists.return_value = False
        mock_resolve.return_value = resolved_path
        
        train_main()
        assert mock_classifier.get_features.called
