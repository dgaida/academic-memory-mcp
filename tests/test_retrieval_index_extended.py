import pytest
from unittest.mock import MagicMock, patch
import numpy as np

@pytest.fixture
def search_index(tmp_path):
    # Patch at the module level where they are used
    with patch("mcp_university.retrieval.index.SentenceTransformer") as mock_st,          patch("mcp_university.retrieval.index.QdrantClient"),          patch("mcp_university.retrieval.index.get_model") as mock_get_model:
        
        st_inst = mock_st.return_value
        st_inst.get_sentence_embedding_dimension.return_value = 128
        st_inst.encode.return_value = np.zeros((1, 128))
        mock_get_model.return_value = st_inst

        from mcp_university.retrieval.index import SearchIndex
        idx = SearchIndex(location=str(tmp_path / "qdrant"), embedding_model_name="test-model")
        idx.use_qmd = False
        yield idx

def test_add_documents(search_index):
    search_index.add_documents([
        {"content": "Some content", "path": "test.txt", "filename": "test.txt"}
    ])
    assert search_index.client.upsert.called

def test_search_minimal(search_index):
    # Test with bm25 = None to avoid complex mocks
    search_index.bm25 = None
    
    mock_point = MagicMock()
    mock_point.payload = {"doc_id": "p1", "filename": "f1", "content": "c1"}
    mock_point.score = 0.9
    
    search_index.client.query_points.return_value.points = [mock_point]
    
    results = search_index.search("query", top_k=1)
    assert len(results) == 1
    assert results[0]['path'] == "p1"

def test_delete_document(search_index):
    search_index.delete_document("test.txt")
    assert search_index.client.delete.called
