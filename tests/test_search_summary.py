import pytest
from unittest.mock import MagicMock, patch
from mcp_university.retrieval.index import SearchIndex


@pytest.fixture
def mock_store():
    store = MagicMock()
    # Mock get_file return: (id, path, hash, mtime, type, last_indexed, folder_id)
    store.get_file.return_value = (
        1,
        "/path/to/doc.pdf",
        "hash",
        123.0,
        ".pdf",
        456.0,
        10,
    )
    store.get_summary.return_value = "This is a summary of the document."
    return store


def test_search_index_enrichment(mock_store, tmp_path):
    # Setup SearchIndex with mock store and disable qmd for this test
    with (
        patch(
            "mcp_university.retrieval.index.SearchIndex._check_qmd", return_value=False
        ),
        patch("mcp_university.retrieval.index.NATIVE_AVAILABLE", True),
        patch("mcp_university.retrieval.index.QdrantClient"),
        patch("mcp_university.retrieval.index.SentenceTransformer"),
    ):
        idx = SearchIndex(location=str(tmp_path), store=mock_store)

        # Mock native search result
        mock_res = MagicMock()
        mock_res.payload = {
            "doc_id": "/path/to/doc.pdf",
            "content": "Original full content",
        }
        mock_res.score = 0.9

        idx.client.query_points.return_value.points = [mock_res]
        idx.bm25 = None  # Disable BM25 for simplicity

        results = idx.search("test query")

        assert len(results) == 1
        assert results[0]["path"] == "/path/to/doc.pdf"
        # Verify that content was replaced by summary
        assert results[0]["content"] == "This is a summary of the document."

        # Verify store calls
        mock_store.get_file.assert_called_with("/path/to/doc.pdf")
        mock_store.get_summary.assert_called_with("file", 1)


def test_crawler_indexes_summary(tmp_path):
    from mcp_university.crawler.crawler import Crawler
    from mcp_university.config import Config

    config = Config()
    config.folders.folders = [str(tmp_path)]
    store = MagicMock()
    parser = MagicMock()
    summarizer = MagicMock()
    index = MagicMock()

    # Setup mocks
    parser.parse.return_value = "full content of the file"
    summarizer.summarize_file.return_value = "file summary"
    store.get_file.return_value = None
    store.upsert_file.return_value = 1

    crawler = Crawler(config, store, parser, summarizer, index)

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    crawler._process_file(test_file, 1)

    # Verify that index.add_document was called with the summary, NOT the full content
    args, kwargs = index.add_document.call_args
    assert args[1] == "file summary"
    assert args[1] != "full content of the file"
