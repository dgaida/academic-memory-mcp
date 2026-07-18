"""Tests to maximize coverage for index.py (SearchIndex).

This module provides unit tests targeting previously uncovered lines and edge cases
in the SearchIndex class.
"""

import os
import sys
import pytest
import json
import pickle
import subprocess
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from mcp_university.retrieval.index import SearchIndex, get_model


@pytest.fixture(autouse=True)
def mock_index_dependencies() -> MagicMock:
    """Fixture to mock SentenceTransformer.

    Returns:
        MagicMock: Mocked SentenceTransformer instance.
    """
    mock_st = MagicMock()
    mock_st.encode.return_value = np.zeros(128)
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_st), \
         patch("mcp_university.retrieval.index.SentenceTransformer", return_value=mock_st):
        yield mock_st


def test_import_error_native_unavailable() -> None:
    """Test importing index.py when native dependencies are missing to cover 20-21.

    Returns:
        None
    """
    import importlib
    import mcp_university.retrieval.index
    with patch.dict(sys.modules, {"qdrant_client": None}):
        importlib.reload(mcp_university.retrieval.index)
        assert not mcp_university.retrieval.index.NATIVE_AVAILABLE

    # Restore native availability for remaining tests
    importlib.reload(mcp_university.retrieval.index)


def test_get_model_offline_error() -> None:
    """Test get_model raises error in offline mode when loading fails.

    Returns:
        None
    """
    with patch("mcp_university.retrieval.index.SentenceTransformer", side_effect=Exception("Load error")):
        with pytest.raises(Exception):
            get_model("test-model", offline=True)


def test_get_model_online_fallback() -> None:
    """Test get_model falls back to Hugging Face loading when offline is False.

    Returns:
        None
    """
    mock_model = MagicMock()
    with patch("mcp_university.retrieval.index.SentenceTransformer", side_effect=[Exception("Local fail"), mock_model]) as mock_init:
        res = get_model("test-model", offline=False)
        assert res == mock_model
        assert mock_init.call_count == 2


def test_native_unavailable_fallback(tmp_path: Path) -> None:
    """Test fallback when NATIVE_AVAILABLE is False.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    with patch("mcp_university.retrieval.index.NATIVE_AVAILABLE", False):
        idx = SearchIndex(location=str(tmp_path / "index"))
        assert not idx._qmd_available

        # Methods should return early / not crash
        assert idx.add_document("doc1", "content", {}) is None
        assert idx.delete_document("doc1") is None
        assert idx.add_documents([{"doc_id": "doc1", "content": "content"}]) is None


def test_qmd_check_failed_handling(tmp_path: Path) -> None:
    """Test when check_qmd fails with FileNotFoundError or CalledProcessError to cover 73, 92-93.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    with patch("subprocess.run", side_effect=FileNotFoundError("no qmd")):
        with patch("mcp_university.retrieval.index.NATIVE_AVAILABLE", False):
            idx = SearchIndex(location=str(tmp_path / "index"))
            assert not idx._qmd_available


def test_load_bm25_load_and_rebuild(tmp_path: Path) -> None:
    """Test _load_bm25 loading corpus and rebuilding BM25 index when pkl is missing.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    loc = tmp_path / "index"
    loc.mkdir()

    corpus_path = loc / "corpus.json"
    corpus_data = [{"doc_id": "doc1", "content": "hello world", "metadata": {}}]
    corpus_path.write_text(json.dumps(corpus_data))

    idx = SearchIndex(location=str(loc))
    assert idx.bm25 is not None
    assert idx.corpus == corpus_data


def test_load_bm25_existing_pkl(tmp_path: Path) -> None:
    """Test _load_bm25 loading BM25 index from existing pkl to cover 143-145.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    loc = tmp_path / "index_with_pkl"
    loc.mkdir()

    corpus_path = loc / "corpus.json"
    corpus_data = [{"doc_id": "doc1", "content": "hello world", "metadata": {}}]
    corpus_path.write_text(json.dumps(corpus_data))

    # We mock BM25Okapi using a helper since rank_bm25 is mocked in conftest
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([["hello", "world"]])

    bm25_path = loc / "bm25_index.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)

    idx = SearchIndex(location=str(loc))
    assert idx.bm25 is not None
    assert idx.corpus == corpus_data


def test_add_document_singular(tmp_path: Path) -> None:
    """Test add_document (singular) with NATIVE_AVAILABLE=True to cover 164-183.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    loc = tmp_path / "add_doc_index"
    loc.mkdir()

    idx = SearchIndex(location=str(loc))
    idx.add_document("doc1.txt", "Some text body here", {"filename": "doc1.txt"})
    assert idx.client.upsert.called
    assert len(idx.corpus) == 1
    assert idx.corpus[0]["doc_id"] == "doc1.txt"


def test_enrich_with_summary_exception(tmp_path: Path) -> None:
    """Test _enrich_with_summary returns default content when store raising exception.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    mock_store = MagicMock()
    mock_store.get_file.side_effect = Exception("Store error")

    idx = SearchIndex(location=str(tmp_path / "index"), store=mock_store)
    res = idx._enrich_with_summary("some/path", "default content")
    assert res == "default content"


def test_search_qmd_regex_mismatch(tmp_path: Path) -> None:
    """Test _search_qmd returns empty list when output does not contain JSON array.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    idx = SearchIndex(location=str(tmp_path / "index"))
    idx.use_shell = False

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "Successful execution but no JSON array here."

    with patch("subprocess.run", return_value=mock_res):
        res = idx._search_qmd("query")
        assert res == []


def test_search_qmd_non_zero_exit_error(tmp_path: Path) -> None:
    """Test _search_qmd error logging when process exits with non-zero code to cover 333.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    idx = SearchIndex(location=str(tmp_path / "index"))
    idx.use_shell = False

    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "CLI simulated error"

    with patch("subprocess.run", return_value=mock_res):
        res = idx._search_qmd("query")
        assert res == []


def test_search_qmd_exception(tmp_path: Path) -> None:
    """Test _search_qmd handles exceptions gracefully and returns empty list.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    idx = SearchIndex(location=str(tmp_path / "index"))
    idx.use_shell = False

    with patch("subprocess.run", side_effect=Exception("Subprocess crash")):
        res = idx._search_qmd("query")
        assert res == []


def test_search_qmd_success_path(tmp_path: Path) -> None:
    """Test _search_qmd parses JSON results correctly and enriches with summary to cover 265-266.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    mock_store = MagicMock()
    mock_store.get_file.return_value = (1, "doc.txt", "hash", 123, "file", 123, 1)
    mock_store.get_summary.return_value = "This is a summary"

    idx = SearchIndex(location=str(tmp_path / "index"), store=mock_store)
    idx.use_shell = False

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = '[{"file": "doc.txt", "title": "Doc", "score": 0.8, "snippet": "snippet"}]'

    with patch("subprocess.run", return_value=mock_res):
        # search() will call _search_qmd first and return results (covering 265-266)
        idx._qmd_available = True
        res = idx.search("query")
        assert len(res) == 1
        assert res[0]["content"] == "This is a summary"
        assert res[0]["score"] == 0.8


def test_search_no_backend_available(tmp_path: Path) -> None:
    """Test search when both qmd and native search backends are unavailable.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    with patch("mcp_university.retrieval.index.NATIVE_AVAILABLE", False):
        idx = SearchIndex(location=str(tmp_path / "index"))
        idx._qmd_available = False

        res = idx.search("query")
        assert res == []


def test_search_qmd_fallback_to_native(tmp_path: Path) -> None:
    """Test search enlists native fallback if qmd returns no results.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    idx = SearchIndex(location=str(tmp_path / "index"))
    idx._qmd_available = True

    with patch.object(idx, "_search_qmd", return_value=[]), \
         patch.object(idx, "_search_native", return_value=[{"path": "native_res"}]) as mock_native:
        res = idx.search("query")
        assert res == [{"path": "native_res"}]
        mock_native.assert_called_once_with("query", 5)


def test_search_native_blending(tmp_path: Path) -> None:
    """Test _search_native blending BM25 scores with Qdrant results (covering 370-376).

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    loc = tmp_path / "index"
    loc.mkdir()

    idx = SearchIndex(location=str(loc))
    # Setup some pre-existing corpus with 5 documents.
    idx.corpus = [
        {"doc_id": "doc1", "content": "hello", "metadata": {"filename": "doc1.txt"}},
        {"doc_id": "doc2", "content": "world", "metadata": {"filename": "doc2.txt"}},
        {"doc_id": "doc3", "content": "foo", "metadata": {"filename": "doc3.txt"}},
        {"doc_id": "doc4", "content": "bar", "metadata": {"filename": "doc4.txt"}},
        {"doc_id": "doc5", "content": "baz", "metadata": {"filename": "doc5.txt"}}
    ]
    idx._rebuild_bm25()

    # Since rank_bm25 is mocked in conftest and always returns zeros,
    # we patch the mock's get_scores method inside our test to return positive scores
    # of size equal to len(idx.corpus).
    idx.bm25.get_scores = MagicMock(return_value=np.array([0.5, 0.8, 0.0, 0.0, 0.0]))

    # Stub query_points returning doc1
    mock_point = MagicMock()
    mock_point.payload = {"doc_id": "doc1", "filename": "doc1.txt", "content": "hello"}
    mock_point.score = 0.5
    idx.client.query_points.return_value = [mock_point]

    # BM25 should score both doc1 and doc2 (doc2 goes into else block, covering 374-376)
    res = idx._search_native("hello world")
    assert len(res) >= 2
    paths = [r["path"] for r in res]
    assert "doc1" in paths
    assert "doc2" in paths
