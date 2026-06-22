import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import numpy as np
import torch
from mcp_university.classifier.train import evaluate_and_save, main as train_main

def test_evaluate_and_save():
    mock_classifier = MagicMock()
    mock_classifier.label_encoder.classes_ = np.array(['Class1', 'Class2'])
    mock_classifier.label_encoder.inverse_transform.side_effect = lambda x: np.array(['Class1', 'Class2'])[x.astype(int)]
    mock_classifier.method = 'transformer'
    mock_classifier.tokenizer.return_value = {'input_ids': torch.tensor([[1]]), 'attention_mask': torch.tensor([[1]])}
    mock_classifier.classifier.return_value = torch.tensor([[1.0, 0.0]])
    
    with patch('mcp_university.classifier.train.plt'),          patch('mcp_university.classifier.train.sns'),          patch('mcp_university.classifier.train.open', mock_open()):
        output_dir = MagicMock(spec=Path)
        # Ensure mkdir is mocked
        output_dir.mkdir = MagicMock()
        evaluate_and_save(mock_classifier, ['text'], ['Class1'], output_dir)
        assert output_dir.mkdir.called

@patch('mcp_university.classifier.train.argparse.ArgumentParser.parse_args')
@patch('mcp_university.classifier.train.EmailClassifier')
@patch('mcp_university.classifier.train.train_test_split')
@patch('mcp_university.classifier.train.resolve_model_path')
@patch('mcp_university.config.get_config')
@patch('mcp_university.classifier.train.get_device')
def test_train_main(mock_dev, mock_cfg, mock_resolve, mock_split, mock_classifier_cls, mock_args):
    mock_args.return_value = MagicMock(data_dir='data', method='transformer', mode='combined', model_path='model.pkl', embedding_model='bert')
    mock_classifier = mock_classifier_cls.return_value
    mock_classifier.preprocess_data.return_value = (['t1', 't2', 't3', 't4'], ['C1', 'C2', 'C1', 'C2'])
    mock_split.return_value = (['t1', 't3'], ['t2', 't4'], ['C1', 'C1'], ['C2', 'C2'])
    
    mock_path = MagicMock(spec=Path)
    mock_path.parent = MagicMock(spec=Path)
    mock_resolve.return_value = mock_path
    
    mock_classifier.tokenizer.side_effect = lambda texts, **kwargs: {'input_ids': torch.zeros((len(texts), 1)), 'attention_mask': torch.ones((len(texts), 1))}
    mock_classifier.label_encoder.transform.side_effect = lambda x: np.zeros(len(x), dtype=int)
    
    # Avoid the local import issue by mocking EmailTransformerClassifier in its home module
    with patch('mcp_university.classifier.engine.EmailTransformerClassifier'):
        train_main()
    assert True
