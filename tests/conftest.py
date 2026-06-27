import sys
from unittest.mock import MagicMock

# Create a class to act as a package with attributes
class MockPackage(MagicMock):
    def __getattr__(self, name):
        return MagicMock()

# Mock heavy dependencies
mock_modules = [
    'torch',
    'torch.nn',
    'transformers',
    'sklearn',
    'sklearn.ensemble',
    'sklearn.feature_extraction',
    'sklearn.feature_extraction.text',
    'sklearn.model_selection',
    'sklearn.metrics',
    'sklearn.metrics.pairwise',
    'sklearn.preprocessing',
    'sklearn.cluster',
    'xgboost',
    'llm_client',
    'ollama',
    'qdrant_client',
    'rank_bm25',
    'sentence_transformers'
]

for mod in mock_modules:
    sys.modules[mod] = MockPackage()
