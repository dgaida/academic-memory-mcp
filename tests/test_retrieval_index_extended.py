"""Tests for test_retrieval_index_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

# Ensure SearchIndex and get_model are mocked wherever they might be used
@pytest.fixture(autouse=True)
def mock_search_dependencies():
    """Test function."""
    mock_st = MagicMock()
    mock_st.get_sentence_embedding_dimension.return_value = 128
    mock_st.encode.return_value = np.zeros((1, 128))

    with patch("sentence_transformers.SentenceTransformer", return_value=mock_st),          patch("mcp_university.retrieval.index.SentenceTransformer", return_value=mock_st),          patch("mcp_university.retrieval.index.get_model", return_value=mock_st),          patch("mcp_university.retrieval.index.QdrantClient") as mock_qdrant:
        yield mock_st, mock_qdrant

def test_add_documents(tmp_path, mock_search_dependencies):
    """Tests test_add_documents."""
    from mcp_university.retrieval.index import SearchIndex
    mock_st, mock_qdrant = mock_search_dependencies

    idx = SearchIndex(location=str(tmp_path / "qdrant"), embedding_model_name="test-model")
    idx.use_qmd = False

    idx.add_documents([
        {"doc_id": "test.txt", "content": "Some content", "path": "test.txt", "filename": "test.txt"}
    ])
    assert idx.client.upsert.called

def test_search_minimal(tmp_path, mock_search_dependencies):
    """Tests test_search_minimal."""
    from mcp_university.retrieval.index import SearchIndex
    mock_st, mock_qdrant = mock_search_dependencies

    idx = SearchIndex(location=str(tmp_path / "qdrant"), embedding_model_name="test-model")
    idx.use_qmd = False
    idx.bm25 = None
    
    mock_point = MagicMock()
    mock_point.payload = {"doc_id": "p1", "filename": "f1", "content": "c1"}
    mock_point.score = 0.9
    
    idx.client.query_points.return_value.points = [mock_point]
    
    results = idx.search("query", top_k=1)
    assert len(results) == 1
    assert results[0]['path'] == "p1"

def test_delete_document(tmp_path, mock_search_dependencies):
    """Tests test_delete_document."""
    from mcp_university.retrieval.index import SearchIndex
    mock_st, mock_qdrant = mock_search_dependencies

    idx = SearchIndex(location=str(tmp_path / "qdrant"), embedding_model_name="test-model")
    idx.use_qmd = False

    idx.delete_document("test.txt")
    assert idx.client.delete.called
