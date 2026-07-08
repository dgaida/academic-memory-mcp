"""Tests for conftest.py."""
import pytest
import sys
import types
from unittest.mock import MagicMock

# Ensure matplotlib uses Agg backend for CI
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

def create_mock_module(name):
    if name in sys.modules:
        return sys.modules[name]
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

# Robustly mock all potentially missing libraries
# win32com
win32 = create_mock_module("win32com")
win32_client = create_mock_module("win32com.client")
win32.client = win32_client
win32_client.Dispatch = MagicMock()

# ollama
ollama = create_mock_module("ollama")
ollama.Client = MagicMock()

# xgboost
xgboost = create_mock_module("xgboost")
xgboost.XGBClassifier = MagicMock

# sentence_transformers
st = create_mock_module("sentence_transformers")
st.SentenceTransformer = MagicMock
create_mock_module("sentence_transformers.models")

# qdrant_client
qc = create_mock_module("qdrant_client")
qc_models = create_mock_module("qdrant_client.models")
qc.models = qc_models
qc.QdrantClient = MagicMock
qc_models.VectorParams = MagicMock
qc_models.Distance = MagicMock()
qc_models.Distance.COSINE = "Cosine"
qc_models.PointStruct = MagicMock
qc_models.Filter = MagicMock
qc_models.FieldCondition = MagicMock
qc_models.MatchValue = MagicMock
qc_models.PointIdsList = MagicMock

# rank_bm25
# Use a real class for BM25Okapi to avoid unhashable type issues in mock init
class MockBM25Okapi:
    def __init__(self, corpus):
        pass
    def get_scores(self, query):
        import numpy as np
        return np.zeros(1)

rank_bm25 = create_mock_module("rank_bm25")
rank_bm25.BM25Okapi = MockBM25Okapi

# shap
shap = create_mock_module("shap")
shap.TreeExplainer = MagicMock

@pytest.fixture
def mock_llm_client_wrapper(monkeypatch):
    """Fixture to mock LLMClientWrapper across all tests."""
    instance = MagicMock()
    instance.model = "test-model"
    instance.chat = MagicMock()
    instance.chat.return_value = {
        'message': {'role': 'assistant', 'content': 'Default mock response', 'tool_calls': None}
    }

    targets = [
        'mcp_university.utils.llm_client_wrapper.LLMClientWrapper',
        'mcp_university.summarizer.engine.LLMClientWrapper',
        'mcp_university.agent.engine.LLMClientWrapper',
        'mcp_university.agent.mcp_agent.LLMClientWrapper',
        'mcp_university.utils.anonymizer.LLMClientWrapper',
    ]

    for target in targets:
        try:
            monkeypatch.setattr(target, MagicMock(return_value=instance))
        except (ImportError, AttributeError):
            pass

    yield instance

@pytest.fixture(autouse=True)
def mock_outlook_dependencies(monkeypatch):
    """Fixture to mock Outlook-related dependencies for all tests."""
    try:
        monkeypatch.setattr('mcp_university.utils.outlook.is_outlook_open', lambda: True)
        monkeypatch.setattr('mcp_university.utils.outlook.OUTLOOK_AVAILABLE', True)
    except (ImportError, AttributeError):
        pass
    yield
