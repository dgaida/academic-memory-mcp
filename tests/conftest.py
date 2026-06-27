import sys
from unittest.mock import MagicMock

# Mock project modules that have heavy dependencies
sys.modules['mcp_university.classifier.engine'] = MagicMock()
sys.modules['mcp_university.utils.torch_utils'] = MagicMock()

# Mock external heavy dependencies
mock_modules = [
    'torch', 'transformers', 'sklearn', 'xgboost', 'sentence_transformers',
    'llm_client', 'ollama', 'qdrant_client', 'rank_bm25'
]
for mod in mock_modules:
    sys.modules[mod] = MagicMock()
